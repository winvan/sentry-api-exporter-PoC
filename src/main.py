import os
import time
from prometheus_client import start_http_server, Histogram, Gauge
import schedule
import threading
import logging
import lognormal
import http_client
import sys

class AppMetrics:
    exported_metric_histogram: Histogram

    def __init__(self, vitals, sentry_address, sentry_token, project, sentry_organization, buffer_interval=3600, sentry_port=443,
                 polling_interval_seconds=5, offset=300):
        self.paths = []
        self.sentry_port = sentry_port
        self.polling_interval_seconds = polling_interval_seconds
        self.sentry_address = sentry_address
        self.sentry_token = sentry_token
        self.sentry_organization = sentry_organization
        self.vitals = vitals
        self.buffer_interval = buffer_interval
        self.exported_metric_histogram = Histogram("sentry_web_vital", "vital", ['path', 'vital', 'project'],
                                                   buckets=(.1, .25, .5, .75,
                                                            1, 1.25, 1.5, 1.75,
                                                            2, 2.25, 2.5, 2.75,
                                                            3, 3.25, 3.5, 3.75,
                                                            4, 4.25, 4.5, 4.75,
                                                            5, 5.25, 5.5, 5.75,
                                                            6, 6.25, 6.5, 6.75,
                                                            7, 7.25, 7.5, 7.75,
                                                            8, 8.25, 8.5, 8.75,
                                                            9, 9.25, 9.5, 9.75,
                                                            10, float("inf")))
        self.exported_metric_healthcheck = Gauge("sentry_exporter_healthcheck", "Just a healthcheck", ['project'])
        self.exported_metric_scoring = Gauge('sentry_scoring', 'scoring', ['path', 'project'])
        self.exported_metric_crash_free_sessions = Gauge('sentry_crash_free_sessions', 'Crash free sessions', ['project'])
        self.offset = offset
        self.project = project
        schedule.every(self.polling_interval_seconds).seconds.do(self.threaded_fetch, self.fetch)
        self.exported_metric_healthcheck.labels(project=self.project).set(1)


    def threaded_fetch(self, job_func):
        job_thread = threading.Thread(target=job_func, args=(self.project,))
        job_thread.start()

    def run_metrics_loop(self):
        logging.warning("Start fetching metrics loop")
        while True:
            schedule.run_pending()
            time.sleep(0.1)

    def fetch(self, project):
        current_timestamp = int(time.time())
        start_timestamp = current_timestamp - self.offset - 60
        end_timestamp = current_timestamp - self.offset
        event: dict
        self.paths = http_client.get_path_list(self, project)
        logging.warning("Start fetching events")
        for path in self.paths:
            events_count = http_client.get_events_count(self, path, project)
            if events_count == 0:
                continue
            pages = (events_count // 100) + 1
            metric_events = http_client.get_events(self, path, pages, project)
            logging.info("Start update histograms")
            events_count = 0
            vitals_average = {}
            for vital in self.vitals:
                vitals_average.update({vital:{'count': 0, 'value': 0}})
            for event in metric_events:
                # if start_timestamp < int(event.get("timestamp")) < end_timestamp:
                if int(event.get("timestamp")) < end_timestamp:
                    events_count += 1
                    logging.info(event.get("id"))
                    for vital in self.vitals:
                        # try:
                        if event.get(f"measurements.{vital}") is not None:
                            prometheus_value = event.get(f"measurements.{vital}")
                            vitals_average[vital]['count'] += 1
                            vitals_average[vital]['value'] += prometheus_value
                            if vital != 'cls':
                                prometheus_value = prometheus_value / 1000
                            if int(event.get("timestamp")) > start_timestamp:
                                self.exported_metric_histogram.labels(path=path, vital=vital, project=project
                                                                  ).observe(prometheus_value)
                            logging.info(f"{path} {vital} updated")
                        # except TypeError:
                        else:
                            logging.info(f"{vital} is Null")

            # scoring
            scoring_enabled = False
            score_metrics = []
            for v, average in vitals_average.items():
                if average['count'] == 0:
                    scoring_enabled = False
                    break
                else:
                    scoring_enabled = True
                    score_metrics.append({'name': v, 'value': average['value'] / average['count']})
            if scoring_enabled:
                self.exported_metric_scoring.labels(project=project, path=path).set(lognormal.compute_perf_score(score_metrics))
            logging.warning(f"Applied {events_count} events using offset {self.offset} (project: {project})")

        # crash_free_sessions
        crash_free_sessions_metric = http_client.get_crash_free_sessions(self, project)
        if crash_free_sessions_metric:
            self.exported_metric_crash_free_sessions.labels(project=project).set(crash_free_sessions_metric)

        logging.warning("End fetching events")

def main():
    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "60"))
    sentry_port = int(os.getenv("SENTRY_PORT", "443"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))
    sentry_address = os.getenv("SENTRY_ADDRESS", "sentry.example.com")
    sentry_token = os.getenv("SENTRY_TOKEN")
    sentry_organization = os.getenv('SENTRY_ORGANIZATION', "example.com")
    log_level = os.getenv("EXPORTER_LOGLEVEL", "warn").upper()
    buffer_interval = int(os.getenv("BUFFER_INTERVAL", "1200"))
    project = os.getenv('SENTRY_PROJECT')
    offset = int(os.getenv("SCRAPE_OFFSET", "300"))
    vitals = {
        "lcp",
        "fcp",
        "cls",
        "fid"
    }

    logging.basicConfig(format='%(asctime)s - %(message)s')
    logging.getLogger().setLevel(level=log_level)

    if sentry_token is None:
        logging.warning("SENTRY_TOKEN is empty")
        sys.exit(1)

    if project is None:
        logging.warning("SENTRY_PROJECT is empty")
        sys.exit(1)

    app_metrics = AppMetrics(
        sentry_port=sentry_port,
        polling_interval_seconds=polling_interval_seconds,
        vitals=vitals,
        sentry_address=sentry_address,
        sentry_token=sentry_token,
        sentry_organization=sentry_organization,
        buffer_interval=buffer_interval,
        offset=offset,
        project=project
    )
    start_http_server(exporter_port)
    app_metrics.run_metrics_loop()


if __name__ == "__main__":
    main()