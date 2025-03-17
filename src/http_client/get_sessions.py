import urllib.parse as parse
import requests
import logging
import math

# Получение статистики сеансов работоспособности релиза
#
# DOCS: https://docs.sentry.io/api/releases/retrieve-release-health-session-statistics/
# EXAMPLE RESPONSE:
#  {
#     "groups":[
#         {
#             "by":{
#                 "session.status":"errored"
#             },
#             "totals":{
#                 "sum(session)":1894
#             },
#         },
#         {
#             "by":{
#                 "session.status":"crashed"
#             },
#             "totals":{
#                 "sum(session)":7660
#             },
#         },
#         {
#             "by":{
#                 "session.status":"abnormal"
#             },
#             "totals":{
#                 "sum(session)":0
#             },
#         },
#         {
#             "by":{
#                 "session.status":"healthy"
#             },
#             "totals":{
#                 "sum(session)":283256
#             },
#         }
#     ]
# }
def get_sessions(host: str, token: str, organization: str, query: any):
    url = parse.urlencode(query, doseq=True, quote_via=parse.quote)
    resp = requests.get(
        url=f"https://{host}/api/0/organizations/{organization}/sessions/?{url}",
        headers={'Authorization': f"Bearer {token}"})
    data = resp.json()

    return data


def get_crash_free_sessions(self, project):
    query = {
        "project": f"{project}",
        "field": "sum(session)",
        "groupBy": "session.status",
        "statsPeriod": f"{self.buffer_interval}s",
    }
    host = f"{self.sentry_address}:{self.sentry_port}"
    token = self.sentry_token
    organization = self.sentry_organization
    data = get_sessions(host, token, organization, query)

    groups = data['groups'] if 'groups' in data else None
    crashed_metrics = None
    if groups:
        crashed_sessions = 0
        total_sessions = 0
        for group in groups:
            # TODO: validate schema
            if 'by' in group and 'session.status' in group['by'] and 'totals' in group and 'sum(session)' in group['totals']:
                session_status = group['by']['session.status']
                sum_session = group['totals']['sum(session)']
                if session_status == 'crashed':
                    crashed_sessions = sum_session
                total_sessions = total_sessions + sum_session

        if total_sessions:
            crashed_metrics_percent = 100 - crashed_sessions / total_sessions * 100
            crashed_metrics = math.floor(crashed_metrics_percent * 1000) / 1000

    logging.warning(f"We can fetch crash_free_sessions {crashed_metrics} for project {project} for statsPeriod {self.buffer_interval}s")

    return crashed_metrics