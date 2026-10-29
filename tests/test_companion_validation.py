import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_companion


class CompanionValidationTests(unittest.TestCase):
    def test_public_companion_has_required_guards(self):
        verify_companion.check_source()


if __name__ == '__main__':
    unittest.main()
