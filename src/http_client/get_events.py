import urllib.parse as parse
import requests
import logging
import calendar
import time

def get_events(self, metric, pages, project):
    logging.info(f"Start fetch events for \"{metric}\"")
    events = []
    for page in range(pages):
        events.extend(get_paged_events(self, metric,page, project))
    return events

def get_paged_events(self, metric, page, project):
    returned_page_events: list
    returned_page_events = []
    url = prepare_paged_url(self, metric,page, project)
    resp = requests.get(
        url=f"https://{self.sentry_address}:{self.sentry_port}/api/0/organizations/{self.sentry_organization}/events/?{url}",
        headers={'Authorization': f"Bearer {self.sentry_token}"})
    paged_events = resp.json()['data']
    logging.info(f"Page {page} fetched")
    for event in paged_events:
        wet_timestamp = event.get("timestamp")
        # 2024-04-13T21:32:54+00:00
        timestamp = calendar.timegm(time.strptime(wet_timestamp, "%Y-%m-%dT%H:%M:%S%z"))
        event.update({"timestamp": timestamp})
        returned_page_events.append(event)
    return returned_page_events

def prepare_paged_url(self, metric, page, project):
    cursor = page * 100
    query = {
        "project": f"{project}",
        "query": f"event.type:transaction transaction:{metric}",
        "statsPeriod": f"{self.buffer_interval}s",
        "cursor": f"0:{cursor}:0",
        "field":   ["id",
                    "timestamp",
                    "measurements.fcp",
                    "measurements.lcp",
                    "measurements.fid",
                    "measurements.cls",
                    "trace"],
        "per_page": "100",
        "sort": "-timestamp"
    }
    url = parse.urlencode(query, doseq=True, quote_via=parse.quote)
    # logging.info(url)
    return url