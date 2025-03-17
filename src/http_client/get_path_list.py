import urllib.parse as parse
import requests
import logging
import sys

def get_path_list(self, project):
    query = {
        "field": [
            "transaction",
            "tpm()"
        ],
        "per_page": "100",
        "project": f"{project}",
        "query": "event.type:transaction transaction.op:pageload",
        "sort": "transaction",
        "statsPeriod": '1h'
    }
    url = parse.urlencode(query, doseq=True, quote_via=parse.quote)
    logging.info(f"paths list URL: {url}")
    # TODO: move to common http library
    resp = requests.get(
        url=f"https://{self.sentry_address}:{self.sentry_port}/api/0/organizations/{self.sentry_organization}/events/?{url}",
        headers={'Authorization': f"Bearer {self.sentry_token}"})
    fetched_paths = resp.json()
    paths = []

    if "detail" in fetched_paths:
        detail = fetched_paths["detail"]
        logging.warning(detail)

        if detail == 'Invalid token':
            sys.exit(1)

    elif "data" in fetched_paths:
        for metric in fetched_paths["data"]:
            paths.append(metric["transaction"])
        logging.info(f"Fetched paths: {paths}")

    return paths