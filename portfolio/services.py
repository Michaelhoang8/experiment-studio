from math import sqrt, erfc
from .validation import ValidationError, text, integer

def wilson(successes, total):
    """95% Wilson score interval for a binomial proportion."""
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - radius), min(1, center + radius)]

def experiment_comparison(a_successes, a_total, b_successes, b_total):
    """Fixed-horizon independent proportions: B minus A, no multiplicity correction."""
    a, b = (a_successes / a_total, b_successes / b_total)
    adjusted_a = (a_successes + 1) / (a_total + 2)
    adjusted_b = (b_successes + 1) / (b_total + 2)
    center = adjusted_b - adjusted_a
    radius = 1.959963984540054 * sqrt(adjusted_a * (1 - adjusted_a) / (a_total + 2) + adjusted_b * (1 - adjusted_b) / (b_total + 2))
    pooled = (a_successes + b_successes) / (a_total + b_total)
    expected = [n * p for n in (a_total, b_total) for p in (pooled, 1 - pooled)]
    enough = min(expected) >= 5
    z = (b - a) / sqrt(pooled * (1 - pooled) * (1 / a_total + 1 / b_total)) if enough else None
    p_value = erfc(abs(z) / sqrt(2)) if enough else None
    return {'difference_interval': [max(-1, center - radius), min(1, center + radius)], 'interval_method': 'Agresti-Caffo', 'confidence_level': 0.95, 'test_method': 'Two-sided pooled two-proportion z-test', 'z_statistic': z, 'p_value': p_value, 'minimum_expected_count': min(expected), 'alpha': 0.05, 'status': 'insufficient_counts' if not enough else 'difference_detected' if p_value < 0.05 else 'inconclusive'}

def experiment_summary(row):
    result = dict(row)
    a = result['a_conversions'] / result['a_visitors']
    b = result['b_conversions'] / result['b_visitors']
    result.update(comparison=experiment_comparison(result['a_conversions'], result['a_visitors'], result['b_conversions'], result['b_visitors']), a_rate=a, b_rate=b, difference=b - a, relative_lift=(b - a) / a if a else None, a_interval=wilson(result['a_conversions'], result['a_visitors']), b_interval=wilson(result['b_conversions'], result['b_visitors']))
    return result

def experiment_create(db, data):
    name = text(data, 'name')
    context = []
    for key, limit in (('hypothesis', 2000), ('primary_metric', 200)):
        value = data.get(key, '')
        if not isinstance(value, str) or len(value.strip()) > limit:
            raise ValidationError(f'{key} must be text of at most {limit} characters')
        context.append(value.strip())
    counts = [integer(data, key, 1 if key.endswith('visitors') else 0) for key in ('a_visitors', 'a_conversions', 'b_visitors', 'b_conversions')]
    if counts[1] > counts[0] or counts[3] > counts[2]:
        raise ValidationError('Conversions cannot exceed visitors')
    with db:
        item_id = db.execute('INSERT INTO experiments(name,a_visitors,a_conversions,b_visitors,b_conversions,hypothesis,primary_metric) VALUES (?,?,?,?,?,?,?)', (name, *counts, *context)).lastrowid
    return {'id': item_id}

def snapshot(db):
    if db.in_transaction:
        return _snapshot_rows(db)
    with db:
        db.execute('BEGIN')
        return _snapshot_rows(db)

def _snapshot_rows(db):
    return {'experiments': [experiment_summary(row) for row in db.execute('SELECT * FROM experiments ORDER BY id DESC')]}
