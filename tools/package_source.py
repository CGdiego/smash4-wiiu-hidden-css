"""Create a source-only ZIP; explicit allowlist prevents dump/secret inclusion."""
import argparse
import re
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_FILES=[
    '.gitignore','README.md','LICENSE',
    'docs/SOURCES.md','docs/VALIDATION.md',
    'tools/smash4.py','tools/build.py','tools/package_source.py',
    'tools/verify_build.py','tests/test_builder.py',
    'tools/build_boot_probes.py','tools/build_giga_probe.py','tools/build_ui_probe.py',
]


def scan(files):
    for relative in files:
        raw=(ROOT/relative).read_bytes()
        text=raw.decode('utf-8')
        patterns=[r'[A-Za-z]:[\\/]+Users[\\/]',r'gh[pousr]_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'-----BEGIN [A-Z ]*PRIVATE KEY-----']
        if any(re.search(pattern,text) for pattern in patterns):
            raise ValueError('Private path/credential pattern in '+relative)
        if len(raw)>250000:
            raise ValueError('Unexpectedly large public source file: '+relative)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',default='dist/smash4-css-source.zip')
    args=parser.parse_args()
    scan(PUBLIC_FILES)
    dest=ROOT/args.out
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as archive:
        for relative in PUBLIC_FILES:
            info=zipfile.ZipInfo(relative,date_time=(2026,10,27,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,(ROOT/relative).read_bytes())
    with zipfile.ZipFile(dest) as archive:
        if set(archive.namelist())!=set(PUBLIC_FILES):
            raise ValueError('Source ZIP allowlist mismatch')
    print('Privacy scan passed; source-only ZIP contains '+str(len(PUBLIC_FILES))+' files.')


if __name__=='__main__':
    main()
