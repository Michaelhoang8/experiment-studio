import math
import statistics
from . import ml_apps
from .validation import ValidationError

def experiment_plan(data):
    baseline = ml_apps.number(data.get('baseline', 0.1), 'Baseline rate', 0.0001, 0.9999)
    lift = ml_apps.number(data.get('absolute_lift', 0.02), 'Absolute lift', 0.0001, 0.99)
    if baseline + lift >= 1:
        raise ValidationError('Baseline plus lift must be below 1')
    power = ml_apps.number(data.get('power', 0.8), 'Power', 0.5, 0.99)
    alpha = ml_apps.number(data.get('alpha', 0.05), 'Alpha', 0.001, 0.2)
    normal = statistics.NormalDist()
    p2 = baseline + lift
    pooled = (baseline + p2) / 2
    n = math.ceil(((normal.inv_cdf(1 - alpha / 2) * math.sqrt(2 * pooled * (1 - pooled)) + normal.inv_cdf(power) * math.sqrt(baseline * (1 - baseline) + p2 * (1 - p2))) / lift) ** 2)
    return {'per_variant': n, 'total': n * 2, 'baseline': baseline, 'detectable_rate': p2, 'power': power, 'alpha': alpha, 'note': 'Approximate two-sided, equal-allocation two-proportion normal design. Assumes independent observations and a fixed horizon; no repeated peeking, clustering, or multiple-testing adjustment.'}
