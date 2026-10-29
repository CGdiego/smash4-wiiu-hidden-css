"""Reject aliases which collapse to one Windows/FAT filesystem path."""
import sys
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_ui_probe import add_ui_records


class PathCollisionTests(unittest.TestCase):
    def test_case_only_aliases_rejected_before_encoding(self):
        resource=SimpleNamespace(entries=[])
        blob=zlib.compress(b'synthetic')
        items=[(name,None,blob,b'synthetic') for name in ['chr_10_Koopag_01.nut','chr_10_KoopaG_01.nut']]
        with self.assertRaisesRegex(ValueError,'Case-insensitive resource path collision'):
            add_ui_records(resource,items)

    def test_collision_with_native_path_rejected(self):
        resource=SimpleNamespace(entries=[SimpleNamespace(path='chr_10_Koopa_01.nut')])
        with self.assertRaisesRegex(ValueError,'Case-insensitive resource path collision'):
            add_ui_records(resource,[('CHR_10_KOOPA_01.NUT',None,b'',b'')])
