import math

# scoring = {
#     'FCP': {'median': 4000, 'falloff': 2000, 'weight': 0.1},
#     'SI': {'median': 5000, 'falloff': 2500, 'weight': 0.1},
#     'LCP': {'median': 6000, 'falloff': 3000, 'weight': 0.25},
#     # 'TTI': {'median': 7300, 'falloff': 2900, 'weight': 0.15},
#     'TBT': {'median': 600, 'falloff': 200, 'weight': 0.30},
#     'CLS': {'median': 0.25, 'falloff': 0.054, 'weight': 0.25},
# }

scoring = {
    'fcp': {'median': 1600, 'p10': 934, 'weight': 0.125},
    'lcp': {'median': 2400, 'p10': 1200, 'weight': 0.275},
    'fid': {'median': 350, 'p10': 150, 'weight': 0.325},
    'cls': {'median': 0.25, 'p10': 0.1, 'weight': 0.275},
}

def erf(x):
    sign = -1 if x < 0 else 1
    x = abs(x)
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    t = 1 / (1 + p * x)
    y = t * (a1 + t * (a2 + t * (a3 + t * (a4 + t * a5))))
    return sign * (1 - y * math.exp(-x * x))

def quantile_at_value(median, p10, value):
    podr = derivePodrFromP10(median, p10)
    location = math.log(median)
    logRatio = math.log(podr/median)
    shape = math.sqrt(1 - 3 * logRatio - math.sqrt((logRatio - 3) * (logRatio - 3) - 8)) / 2
    standardizedX = (math.log(value) - location) / (math.sqrt(2) * shape)
    return (1 - erf(standardizedX)) / 2

def erf_inv(x):
    #  erfinv(-x) = -erfinv(x);
    sign = -1 if x < 0 else 1
    a = 0.147

    log1x = math.log(1 - x*x)
    p1 = 2 / (math.pi * a) + log1x / 2
    sqrtP1Log = math.sqrt(p1 * p1 - (log1x / a))
    return sign * math.sqrt(sqrtP1Log - p1)

def value_at_quantile(median, p10, quantile):
    podr = derivePodrFromP10(median, p10)
    location = math.log(median)
    logRatio =  math.log(podr / median)
    shape = math.sqrt(1 - 3 * logRatio - math.sqrt((logRatio - 3) * (logRatio - 3) - 8)) / 2
    return math.exp(location + shape * math.sqrt(2) * erf_inv(1 - 2 * quantile))

def derivePodrFromP10(median, p10):
    u = math.log(median)
    shape = abs(math.log(p10) - u) / (math.sqrt(2) * 0.9061938024368232)
    inner1 = -3 * shape - math.sqrt(4 + shape * shape)
    podr = math.exp(u + shape/2 * inner1);
    return podr;


def arithmetic_mean(items):
    weight = 0
    sum = 0
    # подразумеваем, что на вход подается список словарей вида:
    # [
    #   {"score": 1, 'weight': 2},
    #   {"score": 3, 'weight': 4}
    # ]
    for item in items:
        # print(item)
        if item['weight'] != 0:
            weight = weight + item['weight']
            sum = sum + item['score'] * item['weight']
    if weight != 0:
        return sum / weight
    else:
        return 0

def get_metric_params(metric_name):
    median = scoring[metric_name]['median']
    p10 = scoring[metric_name]['p10']
    weight = scoring[metric_name]['weight']
    return {'median': median, 'p10': p10, 'weight': weight}


def compute_perf_score(metrics):
    items = []
    # подразумеваем, что на вход получаем список словарей вида:
    # [
    #     {'name': 'FCP', 'value': 20},
    #     {'name': 'LCP', 'value': 60}
    # ]
    for metric in metrics:
        metric_param = get_metric_params(metric['name'])
        score = quantile_at_value(metric_param['median'], metric_param['p10'], metric['value'])
        items.append({'score': score, 'weight': metric_param['weight']})
    # print(arithmetic_mean(items)*100)
    return arithmetic_mean(items)*100

def main():
    metrics = [
        {'name': 'fcp', 'value': 500},
        {'name': 'lcp', 'value': 1530},
        {'name': 'fid', 'value': 500},
        {'name': 'cls', 'value': 0.1}
    ]
    compute_perf_score(metrics)


if __name__ == "__main__":
    main()
