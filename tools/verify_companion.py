"""Validate the public companion source and, optionally, a locally built WUPS file."""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_native_candidate import rpx_sections

SOURCE = ROOT / 'companion' / 'main.c'
REQUIRED = (
    'US_TITLE_ID UINT64_C(0x0005000010144F00)',
    'ENTRY_INIT_ADDRESS 0x02E45558u',
    'GIGA_ASSIGNMENT_ADDRESS 0x02E45708u',
    'entry != NULL', '*kind == 58u', '*alternate == 15u', '*alternate = 58u',
    'module.textSize', 'code_matches()', '304, 304',
)
PRIVATE = (r'[A-Za-z]:[\\/]+Users[\\/]', r'gh[pousr]_[A-Za-z0-9]{20,}',
           r'github_pat_[A-Za-z0-9_]{20,}', r'PRIVATE KEY')


def check_source():
    text = SOURCE.read_text(encoding='utf-8')
    missing = [item for item in REQUIRED if item not in text]
    if missing:
        raise ValueError('Missing companion safety requirement(s): ' + ', '.join(missing))
    if any(re.search(pattern, text) for pattern in PRIVATE):
        raise ValueError('Private path or credential-like content in companion source')


def check_plugin(path):
    raw = Path(path).read_bytes()
    if raw[:4] != b'\x7fELF' or raw[9:11] != b'PL':
        raise ValueError('Expected a WUPS-marked ELF/RPL plugin')
    payload = b''.join(data for _, data in rpx_sections(path))
    text = payload.decode('latin-1', errors='ignore')
    if any(re.search(pattern, text) for pattern in PRIVATE):
        raise ValueError('Private path or credential-like content in built plugin')
    for expected in ('Hidden CSS Giga Respawn', 'US v304'):
        if expected not in text:
            raise ValueError('Built plugin is missing expected metadata: ' + expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', help='optional local .wps output to audit')
    args = parser.parse_args()
    check_source()
    if args.plugin:
        check_plugin(args.plugin)
    print('Companion source' + (' and plugin' if args.plugin else '') + ' validation passed.')


if __name__ == '__main__':
    main()
