import urllib.parse as parse
import requests
import logging

def get_events_count(self, path, project):
    query = {
        "project": f"{project}",
        "query": f"event.type:transaction transaction:{path}",
        "statsPeriod": f"{self.buffer_interval}s",
        "cursor": "0:0:0",
        "field": "count()",
        "per_page": "50"
    }
    url = parse.urlencode(query, doseq=True, quote_via=parse.quote)
    resp = requests.get(
        url=f"https://{self.sentry_address}:{self.sentry_port}/api/0/organizations/{self.sentry_organization}/events/?{url}",
        headers={'Authorization': f"Bearer {self.sentry_token}"})
    status_data = resp.json()
    events_count = status_data['data'][0]["count()"]
    logging.info(f"We can fetch {events_count} events for path {path} for last {self.buffer_interval} seconds")

    return events_count