from http.client import HTTPConnection
import json
import csv
import io
import tempfile
import threading
import socket
import http.client
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from portfolio.db import initialize, connect
from portfolio import services as s
from portfolio.server import handler_for
from portfolio.validation import ValidationError, ConflictError

class DomainTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'test.db')
        initialize(self.path)
        self.db = connect(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_experiment_context_is_optional_validated_and_preserved(self):
        base = {'name': 'Context', 'a_visitors': 100, 'a_conversions': 10, 'b_visitors': 100, 'b_conversions': 12}
        s.experiment_create(self.db, base)
        original = s.snapshot(self.db)['experiments'][0]
        self.assertEqual((original['hypothesis'], original['primary_metric']), ('', ''))
        s.experiment_create(self.db, {**base, 'hypothesis': '  Clearer copy improves checkout.  ', 'primary_metric': ' Purchases per visitor '})
        contextual = s.snapshot(self.db)['experiments'][0]
        self.assertEqual(contextual['hypothesis'], 'Clearer copy improves checkout.')
        self.assertEqual(contextual['primary_metric'], 'Purchases per visitor')
        self.assertEqual(contextual['comparison'], original['comparison'])
        for key, limit in (('hypothesis', 2000), ('primary_metric', 200)):
            for value in (None, 42, [], {}, 'x' * (limit + 1)):
                with self.subTest(key=key, value=type(value)), self.assertRaises(ValidationError):
                    s.experiment_create(self.db, {**base, key: value})
        self.assertEqual(len(s.snapshot(self.db)['experiments']), 2)

    def test_experiment_rates_and_zero_baseline(self):
        s.experiment_create(self.db, {'name': 'CTA', 'a_visitors': 100, 'a_conversions': 0, 'b_visitors': 100, 'b_conversions': 10})
        result = s.snapshot(self.db)['experiments'][0]
        self.assertIsNone(result['relative_lift'])
        self.assertAlmostEqual(result['difference'], 0.1)
        self.assertAlmostEqual(s.wilson(50, 100)[0], 0.4038315, places=6)
        for successes in [0, 50, 100]:
            lower, upper = s.wilson(successes, 100)
            self.assertTrue(0 <= lower <= upper <= 1)

    def test_comparison_matches_published_nist_examples(self):
        result = s.experiment_comparison(32, 38, 39, 44)
        self.assertAlmostEqual(result['z_statistic'], 0.5864, places=5)
        self.assertAlmostEqual(result['p_value'], 0.5576, delta=1e-05)
        interval = s.experiment_comparison(8, 40, 11, 30)['difference_interval']
        self.assertAlmostEqual(interval[0], -0.04794, places=5)
        self.assertAlmostEqual(interval[1], 0.36936, places=5)

    def test_comparison_reverses_direction_but_not_evidence(self):
        forward = s.experiment_comparison(100, 1000, 150, 1000)
        reverse = s.experiment_comparison(150, 1000, 100, 1000)
        self.assertEqual(forward['status'], 'difference_detected')
        self.assertAlmostEqual(forward['p_value'], reverse['p_value'])
        self.assertAlmostEqual(forward['z_statistic'], -reverse['z_statistic'])
        self.assertAlmostEqual(forward['difference_interval'][0], -reverse['difference_interval'][1])
        same = s.experiment_comparison(50, 100, 50, 100)
        self.assertEqual(same['p_value'], 1)
        self.assertEqual(same['status'], 'inconclusive')

    def test_sparse_comparison_has_no_misleading_p_value(self):
        for counts in [(0, 100, 0, 100), (100, 100, 100, 100), (1, 10, 2, 10), (0, 1, 1, 1)]:
            with self.subTest(counts=counts):
                result = s.experiment_comparison(*counts)
                self.assertIsNone(result['p_value'])
                self.assertIsNone(result['z_statistic'])
                self.assertEqual(result['status'], 'insufficient_counts')
                low, high = result['difference_interval']
                self.assertTrue(-1 <= low < high <= 1)

    def test_invalid_counts_and_bool_rejected(self):
        for visitors, conversions in [(0, 0), (10, 11), (True, 1)]:
            with self.assertRaises(ValidationError):
                s.experiment_create(self.db, {'name': 'Invalid', 'a_visitors': visitors, 'a_conversions': conversions, 'b_visitors': 10, 'b_conversions': 2})
if __name__ == '__main__':
    unittest.main()
