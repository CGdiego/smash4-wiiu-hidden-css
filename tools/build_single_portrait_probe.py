"""Test 05: reroute one native portrait record, without adding RF entries."""
import hashlib
import json
import shutil
import struct
import zipfile
from pathlib import Path
from smash4 import Resource, u32, sortkey

DONOR='ui/replace/chr/chr_10/chr_10_Koopa_01.nut'
TARGET='ui/replace/chr/chr_10/chr_10_Koopag_01.nut'


def reroute_portrait(encoded):
    r=Resource(encoded)
    before=bytes(r.data)
    entry=next(e for e in r.entries if e.path==DONOR)
    if any(e.path==TARGET for e in r.entries):raise ValueError('Target already exists')
    siblings=[e for e in r.entries if e.path.startswith('ui/replace/chr/chr_10/')]
    i=siblings.index(entry)
    if not sortkey(siblings[i-1].path)<sortkey(TARGET)<sortkey(siblings[i+1].path):
        raise ValueError('Renamed record would violate native resource order')
    strings=u32(r.header,32)
    extpos=strings+4+u32(r.data,strings)*8192
    # Use only pre-existing trailing zero padding in the string blocks.
    zero_start=extpos
    while zero_start>strings+4 and r.data[zero_start-1]==0:zero_start-=1
    at=zero_start+32
    name=Path(TARGET).stem.encode('ascii')+b'\0'
    offset=at-(strings+4)
    if at+len(name)>extpos or offset//8192!=(offset+len(name)-1)//8192:
        raise ValueError('No safe native name-padding span')
    if any(r.data[at:at+len(name)]):raise ValueError('Name-padding span is occupied')
    namebits=(u32(r.data,entry.table_offset+4)&0xff000000)|offset
    struct.pack_into('<I',r.data,entry.table_offset+4,namebits)
    r.data[at:at+len(name)]=name
    result=r.encode()
    checked=Resource(result)
    lookup={e.path:e for e in checked.entries}
    if len(checked.entries)!=len(r.entries) or DONOR in lookup or TARGET not in lookup:
        raise ValueError('Unexpected record/path change')
    if checked.header[32:44]!=r.header[32:44]:raise ValueError('RF layout/count changed')
    # Recompression may change the compressed-size header word, not body layout.
    allowed=set(range(24,28))|set(range(entry.table_offset+4,entry.table_offset+8))|set(range(at,at+len(name)))
    if len(before)!=len(checked.data):raise ValueError('RF decompressed size changed')
    if any(a!=b and i not in allowed for i,(a,b) in enumerate(zip(before,checked.data))):
        raise ValueError('Unrelated decompressed resource bytes changed')
    for old in r.entries:
        new=lookup[TARGET if old.path==DONOR else old.path]
        if (old.offset,old.compressed,old.decompressed,old.flags)!=(new.offset,new.compressed,new.decompressed,new.flags):
            raise ValueError('Archive metadata changed')
    return result,{'name_offset':offset,'native_entry_index':entry.index,'record_count_unchanged':True,'all_archive_metadata_unchanged':True,'source_sha256':hashlib.sha256(encoded).hexdigest(),'output_sha256':hashlib.sha256(result).hexdigest()}


def main():
    root=Path(__file__).resolve().parents[1]
    source=root/'build/aroma-giga-slot-probe-v1/wiiu/sdcafiine/0005000010144F00/03-GigaBowser-SeparateSlot/content/patch'
    out=root/'build/aroma-single-portrait-probe-v2'
    dest=out/'wiiu/sdcafiine/0005000010144F00/05-GigaBowser-SinglePortrait/content/patch'
    if out.exists():raise ValueError('Output already exists')
    shutil.copytree(source,dest)
    report={'runtime_tested':False,'base':'03-GigaBowser-SeparateSlot','change':'Temporary reassignment of normal Bowser CSS portrait to Giga Bowser','donor':DONOR,'target':TARGET,'nameplates_added':False,'aliases_added':False,'respawn_results_fixed':False,'partitions':{}}
    for file in dest.glob('resource*'):
        result,audit=reroute_portrait(file.read_bytes())
        file.write_bytes(result)
        report['partitions'][file.name]=audit
    for original in source.rglob('*'):
        if original.is_file() and not original.name.startswith('resource'):
            if original.read_bytes()!=(dest/original.relative_to(source)).read_bytes():
                raise ValueError('Non-resource file changed')
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'READ-ME.txt').write_text(
        'AROMA TEST 05: ONE PORTRAIT, NO NEW RESOURCE RECORDS\n'
        'Copy wiiu to SD root. Select 05-GigaBowser-SinglePortrait alone.\n'
        'Do not merge with earlier packs. Test03 remains the working baseline.\n'
        'This temporarily gives normal Bowser CSS artwork to the extra Giga Bowser slot.\n'
        'Normal Bowser may therefore have a blank icon; this tradeoff is diagnostic only.\n'
        'Giga Bowser nameplate remains absent: no nameplates or aliases were added.\n'
        'All packed files and patchlist are byte-identical to test03.\n'
        'No resource entries, external flags, name blocks or archive offsets were added.\n'
        'Report: boot, CSS load, which slot gets the Bowser portrait, Training load/exit.\n'
        'Respawn/results bugs remain. Avoid finishing matches.\n'
        'Select test03 again to restore its original icons.\n',encoding='utf-8')
    archive=root/'dist/aroma-single-portrait-probe-v2.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in out.rglob('*'):
            if file.is_file():z.write(file,file.relative_to(out).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP integrity failure')
    print('Verified all four partitions: one portrait rerouted; all record counts, packed archives and patchlist preserved. Runtime not tested.')
    print(archive)


if __name__=='__main__':main()
