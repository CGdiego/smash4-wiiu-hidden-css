"""Check an official export against private inputs and the unmodified dump.

This verifies archive contents, not runtime stability or fighter lifecycle.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from smash4 import Dump, Resource, Params, owns_pack
from build import DB, FIGHTERS, edit_database


def patch_paths(raw):
    if len(raw)<128 or raw[:4]!=b'\x01\x00PL':raise ValueError('Invalid patchlist header')
    count=struct.unpack_from('<I',raw,4)[0]
    if len(raw)!=128*(count+1):raise ValueError('Patchlist record count/length mismatch')
    paths=[]
    for i in range(count):
        record=raw[128*(i+1):128*(i+2)]
        if b'\0' not in record:raise ValueError('Unterminated patchlist path')
        name=record.split(b'\0',1)[0].decode('ascii')
        if not name or '\\' in name or name.startswith('/') or ':' in name or any(p in ('','.','..') for p in name.split('/')):
            raise ValueError('Invalid patchlist path')
        paths.append(name)
    if len({p.casefold() for p in paths})!=len(paths):raise ValueError('Duplicate patchlist path')
    return set(paths)


def decode(blob, size):
    raw=zlib.decompress(blob) if blob[:2] in (b'\x78\x9c',b'\x78\xda',b'\x78\x01') else blob
    if len(raw)!=size:raise ValueError('Archive member length mismatch')
    return raw


class Export:
    def __init__(self, patch, dump):
        self.patch=Path(patch)
        self.dump=dump
        self.resources={p:Resource((self.patch/p.replace('data','resource',1)).read_bytes()) for p in dump.resources}
        self.directories={p:{e.path:e for e in r.entries if e.directory} for p,r in self.resources.items()}
        self.lookup={p:{e.path:e for e in r.entries} for p,r in self.resources.items()}
        self.cache={}

    def member(self, part, entry):
        parent=entry.path.rsplit('/',1)[0]+'/'
        while parent not in self.directories[part] or not self.directories[part][parent].flags&0x400:
            parent=parent.rstrip('/').rsplit('/',1)[0]+'/'
            if parent=='/':raise ValueError('Missing packed ancestor')
        physical=part if entry.flags&0x800 else 'data'
        relative=physical+'/'+parent+'packed'
        path=self.patch/relative
        if relative not in self.cache:
            self.cache[relative]=path.read_bytes() if path.is_file() else self.dump.pack(physical,self.directories[part][parent])
        pack=self.cache[relative]
        blob=pack[entry.offset:entry.offset+entry.compressed]
        if len(blob)!=entry.compressed:raise ValueError('Archive offset out of bounds: '+relative)
        return decode(blob,entry.decompressed)


def verify(root, patch, manifest):
    dump=Dump(root/'Games/Super Smash Bros/content',root/'Updates/Super Smash Bros/content')
    export=Export(patch,dump)
    original_export=Export(dump.patch,dump)
    for part,dirs in export.directories.items():
        for packed in (Path(patch)/part).rglob('packed'):
            parent_path=packed.parent.relative_to(Path(patch)/part).as_posix()+'/'
            if parent_path not in dirs:raise ValueError('Exported pack lacks a folder record')
            parent=dirs[parent_path]
            native=original_export.directories[part].get(parent_path)
            if native is None or not owns_pack(part,native):
                raise ValueError('Partial language pack shadows shared data: '+part+'/'+parent_path)
            if packed.stat().st_size!=parent.compressed:raise ValueError('Packed folder size differs from physical file')
    affected={p:tuple(f.relative_to(Path(patch)/p).as_posix().removesuffix('packed') for f in (Path(patch)/p).rglob('packed')) for p in dump.resources}
    inputs=json.loads(Path(manifest).read_text(encoding='utf-8'))
    expected={}
    for item in inputs:
        source=Path(item['source'])
        part,relative=(item['directory']+source.name).split('/',1)
        expected[part,relative]=source.read_bytes()
    checked=flag_changes=inherited=0
    imported=set()
    for part,resource in export.resources.items():
        paths=[e.path.casefold() for e in resource.entries]
        if len(paths)!=len(set(paths)):raise ValueError('Case-insensitive RF collision: '+part)
        originals={e.path:e for e in dump.resources[part].entries}
        if not originals.keys()<=export.lookup[part].keys():raise ValueError('Original RF entries lost')
        for e in resource.entries:
            if e.directory:continue
            key=part,e.path
            if key in expected:
                if export.member(part,e)!=expected[key]:raise ValueError('Imported bytes differ: '+e.path)
                imported.add(key)
            elif part!='data' and ('data',e.path) in expected:
                if e.flags&0x800:raise ValueError('Unexpected localized override of shared import')
                if export.member(part,e)!=expected['data',e.path]:raise ValueError('Inherited shared import differs')
                inherited+=1
            elif e.path not in originals:raise ValueError('Unexpected new file: '+e.path)
            else:
                old=originals[e.path]
                flag_changes+=int(e.flags!=old.flags)
                if (e.flags^old.flags)&~0x800:raise ValueError('Unexpected flag changes outside localization bit')
                # Exporter may repack/recompress. Compare decoded bytes whenever
                # offsets, compression or sizes differ or the physical pack changed.
                physical=part if e.flags&0x800 else 'data'
                if (e.offset,e.compressed,e.decompressed)!=(old.offset,old.compressed,old.decompressed) or e.path.startswith(affected[physical]):
                    original=original_export.member(part,old)
                    if export.member(part,e)!=original:raise ValueError('Unintended content edit: '+part+'/'+e.path)
                    checked+=1
        database=Params(export.member(part,export.lookup[part][DB]))
        native_db=original_export.member(part,originals[DB])
        exact_db,_=edit_database(native_db,FIGHTERS)
        if bytes(database.data)!=exact_db:raise ValueError('Database has unintended field changes')
        if len(database.groups[0])!=82:raise ValueError('Roster dimensions changed')
        for f in FIGHTERS:
            v=database.values(database.groups[0][f['row']])
            if (v[0],v[6],v[7],v[9])!=(f['cosmetic'],f['id'],1,0):raise ValueError('Roster mismatch')
    if imported!=expected.keys():raise ValueError('Manifest imports missing from resource tables')
    files={p.relative_to(patch).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(patch).rglob('*') if p.is_file()}
    paths=patch_paths((Path(patch)/'patchlist').read_bytes())
    original_paths=patch_paths((dump.patch/'patchlist').read_bytes())
    if not original_paths<=paths:raise ValueError('Original patchlist files omitted')
    replacements={p for p in files if p not in ('patchlist','resource','resource(us_en)','resource(us_fr)','resource(us_sp)')}
    if not replacements<=paths:raise ValueError('Generated physical files missing from patchlist')
    return {'validation_schema':2,'physical_partition_layout_verified':True,'archive_validation_passed':True,'runtime_tested':False,'complete':False,'imported_files_verified':len(imported),'inherited_shared_imports_verified':inherited,'unchanged_members_verified':checked,'patchlist_records_verified':len(paths),'exporter_flag_changes':flag_changes,'files':files}


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--patch',required=True)
    cli.add_argument('--manifest',default='.private/official-inputs.json')
    cli.add_argument('--report',default='build/official-verification.json')
    args=cli.parse_args()
    root=Path(__file__).resolve().parents[1]
    result=verify(root,Path(args.patch),Path(args.manifest))
    Path(args.report).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS:',result['imported_files_verified'],'imports and',result['unchanged_members_verified'],'unchanged archive members; runtime stability unverified.')
