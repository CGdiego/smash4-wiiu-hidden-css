"""Verify output hashes, slot edits, RF metadata and original archive members."""
import argparse
import hashlib
import json
from pathlib import Path
from smash4 import Dump, Resource, Params
from build import DB, FIGHTERS, edit_database


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',required=True)
    parser.add_argument('--update',required=True)
    parser.add_argument('--build',required=True)
    args=parser.parse_args()
    root=Path(args.build)
    report=json.loads((root/'BUILD-REPORT.json').read_text(encoding='utf-8'))
    for path,digest in report['files'].items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
            raise ValueError('Build hash mismatch: '+path)
    dump=Dump(args.game,args.update)
    content=next(root.glob('sdcafiine/*/*/content/patch'))
    fighters=FIGHTERS[:4] if report['profile']=='forms' else FIGHTERS
    checked_files=checked_packs=0
    for partition,original in dump.resources.items():
        resource=Resource((content/partition.replace('data','resource',1)).read_bytes())
        lookup={e.path:e for e in resource.entries}
        for e in original.entries:
            if e.path not in lookup:
                raise ValueError('Original resource omitted: '+e.path)
            n=lookup[e.path]
            if not e.directory and e.path!=DB:
                if (e.offset,e.compressed,e.decompressed,e.flags)!=(n.offset,n.compressed,n.decompressed,n.flags):
                    raise ValueError('Unexpected original file metadata change: '+e.path)
                checked_files+=1
        for file in (content/partition).rglob('packed'):
            parent_path=file.relative_to(content/partition).as_posix()[:-6]
            parent=next(e for e in original.entries if e.path==parent_path)
            old=dump.pack(partition,parent)
            new=file.read_bytes()
            if new[:len(old)]!=old:
                raise ValueError('Original packed bytes changed: '+parent_path)
            checked_packs+=1
        raw,_,parent=dump.read(partition,DB)
        expected,slots=edit_database(raw,fighters)
        entry=lookup[DB]
        packed=(content/partition/parent.path/'packed').read_bytes()
        import zlib
        got=zlib.decompress(packed[entry.offset:entry.offset+entry.compressed])
        if got!=expected or slots!=report['partitions'][partition]['slots']:
            raise ValueError('Slot edits do not match profile')
        p=Params(got)
        if len(p.groups[0])!=84:
            raise ValueError('Expected exactly two appended database rows')
    print(f'PASS: {checked_files} original file records and {checked_packs} archive prefixes preserved; all output hashes and roster edits verified. Runtime gameplay remains untested.')


if __name__=='__main__':
    raise SystemExit('Retired custom-export verifier. Use verify_official_candidate.py; it checks the 82-row official-export candidate.')
