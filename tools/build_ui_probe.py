"""Test 04: add external UI overrides while retaining all native RF records."""
import bisect
import json
import shutil
import struct
import zipfile
import zlib
from pathlib import Path
from smash4 import Dump, Resource, sortkey, u32


def add_ui_records(resource, items):
    """Insert records without discarding native hidden/empty-directory records."""
    native=resource.data
    start=u32(native,12)
    start+=u32(native,start)*8+4
    start+=u32(native,start)+4
    count=u32(native,40)
    end=start+count*24
    strings=u32(native,32)
    blocks=u32(native,strings)
    extpos=strings+4+blocks*8192
    names=bytearray(native[strings:extpos])
    extra=bytearray()
    visible=sorted(resource.entries,key=lambda e:sortkey(e.path))
    keys=[sortkey(e.path) for e in visible]
    insertions={}
    for path,donor,blob,raw in sorted(items,key=lambda item:sortkey(item[0])):
        name=Path(path).stem.encode('ascii')+b'\0'
        namebits=(u32(native,donor.table_offset+4)&0xff000000)|(blocks*8192+len(extra))
        extra+=name
        following=bisect.bisect_left(keys,sortkey(path))
        if following==len(visible):raise ValueError('UI record insertion outside native tree')
        at=visible[following].table_offset
        # Existing game entries use 0x4000 to load an external patch file.
        record=struct.pack('<6I',donor.offset,namebits,len(blob),len(raw),0,donor.flags|0x4000)
        insertions.setdefault(at,[]).append(record)
    if len(extra)>8192:raise ValueError('New strings exceed one block')
    table=bytearray(native[128:start])
    retained=[]
    for at in range(start,end,24):
        for record in insertions.get(at,[]):table+=record
        record=bytes(native[at:at+24])
        table+=record
        retained.append(record)
    if b''.join(retained)!=native[start:end]:raise ValueError('Native records changed')
    table+=native[end:strings]
    while (128+len(table))%16:table.append(0xbb)
    names+=extra+bytes(8192-len(extra))
    struct.pack_into('<I',names,0,blocks+1)
    # Extension table and trailing padding remain byte-identical.
    names+=native[extpos:]
    body=table+names
    header=bytearray(native[:128])
    struct.pack_into('<I',header,16,u32(native,16)+24*len(items))
    struct.pack_into('<III',header,32,128+len(table),u32(native,36)+8192,count+len(items))
    compressed=zlib.compress(body,6)
    struct.pack_into('<II',header,24,len(compressed),len(body))
    encoded=bytes(header)+compressed
    checked=Resource(encoded)
    lookup={e.path:e for e in checked.entries}
    for old in resource.entries:
        new=lookup[old.path]
        if checked.data[new.table_offset:new.table_offset+24]!=native[old.table_offset:old.table_offset+24]:
            raise ValueError('Original resource record changed: '+old.path)
    if len(checked.entries)!=len(resource.entries)+len(items):raise ValueError('Record count mismatch')
    for path,donor,blob,raw in items:
        e=lookup[path]
        if not e.flags&0x4000 or (e.compressed,e.decompressed)!=(len(blob),len(raw)):
            raise ValueError('Incorrect external override metadata')
        if zlib.decompress(blob)!=raw:raise ValueError('Invalid UI compression')
    return encoded


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'build/aroma-giga-slot-probe-v1/wiiu/sdcafiine/0005000010144F00/03-GigaBowser-SeparateSlot/content/patch'
    out=root/'build/aroma-giga-ui-probe-v1'
    dest=out/'wiiu/sdcafiine/0005000010144F00/04-GigaBowser-UI/content/patch'
    if out.exists():raise ValueError('Output already exists')
    shutil.copytree(source,dest)
    dump=Dump(root/'Games/Super Smash Bros/content',root/'Updates/Super Smash Bros/content')
    report={'runtime_tested':False,'base':'03-GigaBowser-SeparateSlot','artwork':'Unmodified Bowser portrait/nameplate placeholders','respawn_results_fix':False,'partitions':{}}
    added_paths=[]
    for partition in dump.resources:
        name=partition.replace('data','resource',1)
        r=Resource((dest/name).read_bytes())
        items=[]
        for donor in r.entries:
            if not donor.path.startswith('ui/replace/chr/') or not donor.path.endswith('_Koopa_01.nut'):continue
            raw,_,_=dump.read(partition,donor.path)
            blob=zlib.compress(raw,6)
            # Both UI-name spellings occur in the executable; match either lookup.
            for alias in ('Koopag','KoopaG'):
                target=donor.path.replace('_Koopa_01.nut','_'+alias+'_01.nut')
                if any(e.path==target for e in r.entries):raise ValueError('Target already exists')
                items.append((target,donor,blob,raw))
                file=dest/partition/target
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(blob)
                added_paths.append(partition+'/'+target)
        if len(items)!=22:raise ValueError('Expected eleven donor UI categories with two aliases')
        (dest/name).write_bytes(add_ui_records(r,items))
        report['partitions'][partition]={'new_external_ui_files':len(items),'all_native_records_preserved':True,'all_packed_archives_unchanged_from_test03':True}
    patchlist=bytearray((source/'patchlist').read_bytes())
    paths={bytes(patchlist[128+i*128:256+i*128]).split(b'\0')[0].decode('ascii') for i in range(u32(patchlist,4))}
    paths.update(added_paths)
    header=patchlist[:128]
    struct.pack_into('<I',header,4,len(paths))
    (dest/'patchlist').write_bytes(header+b''.join(p.encode('ascii').ljust(128,b'\0') for p in sorted(paths,key=sortkey)))
    for file in source.rglob('packed'):
        if file.read_bytes()!=(dest/file.relative_to(source)).read_bytes():raise ValueError('Test03 pack changed')
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'READ-ME.txt').write_text(
        'TEST 04 - GIGA BOWSER UI PLACEHOLDERS\n'
        'Copy wiiu to SD root. Select 04-GigaBowser-UI alone; never merge test packs.\n'
        'Expected: extra Giga Bowser slot now has a normal Bowser portrait and BOWSER nameplate.\n'
        'These are deliberate unmodified placeholders, not custom Giga Bowser artwork/text.\n'
        'This tests external UI overrides and native-record-preserving RF insertion.\n'
        'All packed files are byte-identical to working test03.\n'
        'Report boot, CSS icon, nameplate and Training load/exit.\n'
        'Respawn still restores Bowser. Results softlock is NOT fixed; avoid finishing matches.\n',encoding='utf-8')
    archive=root/'dist/aroma-giga-ui-probe-v1.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in out.rglob('*'):
            if file.is_file():z.write(file,file.relative_to(out).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP integrity failure')
    print('Verified: 88 external UI overrides; all native records and test03 packed files preserved. Runtime untested.')
    print(archive)


if __name__=='__main__':
    main()
