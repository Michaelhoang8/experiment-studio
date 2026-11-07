import json
import csv
import io
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from portfolio import capabilities as c, ml_apps as ml, services
from portfolio.db import initialize, connect, SCHEMA
from portfolio.validation import ValidationError, NotFoundError

class AnalysisCapabilities(unittest.TestCase):

    def test_experiment_planner_power_and_effect_size(self):
        base = c.experiment_plan({})
        self.assertTrue(3800 < base['per_variant'] < 3900)
        self.assertGreater(c.experiment_plan({'power': 0.9})['per_variant'], base['per_variant'])
        self.assertLess(c.experiment_plan({'absolute_lift': 0.04})['per_variant'], base['per_variant'])
        with self.assertRaises(ValidationError):
            c.experiment_plan({'baseline': 0.9, 'absolute_lift': 0.2})
if __name__ == '__main__':
    unittest.main()
