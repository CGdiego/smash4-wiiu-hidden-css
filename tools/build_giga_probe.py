"""Aroma fighter-load probe: Bowser's existing CSS button loads fighter 58."""
import hashlib
import argparse
import json
import zipfile
import zlib
from pathlib import Path
from smash4 import Dump, Params, Resource


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--separate-slot',action='store_true')
    separate=cli.parse_args().separate_slot
    root=Path(__file__).resolve().parents[1]
    dump=Dump(root/'Games/Super Smash Bros/content',root/'Updates/Super Smash Bros/content')
    basename='aroma-giga-slot-probe-v1' if separate else 'aroma-giga-probe-v1'
    packname='03-GigaBowser-SeparateSlot' if separate else '02-GigaBowser-BowserSlot'
    out=root/'build'/basename
    if out.exists():
        raise ValueError('Output exists')
    dest=out/'wiiu/sdcafiine/0005000010144F00'/packname/'content/patch'
    dest.mkdir(parents=True)
    report={'runtime_tested':False,'mode':'fighter-load probe; replaces Bowser selection, does not expand CSS','edits':{'row':16,'cosmetic_id_unchanged':16,'field_6_character_id':[15,58],'field_7_costumes':[8,1],'field_5_victory':[1,0]},'partitions':{}}
    for partition,resource in dump.resources.items():
        rf_name=partition.replace('data','resource',1)
        original_rf=Resource((dump.patch/rf_name).read_bytes())
        raw,entry,parent=dump.read(partition,'param/ui/ui_character_db.bin')
        params=Params(raw)
        row=params.groups[0][16]
        values=params.values(row)
        if (values[0],values[6],values[7],values[5])!=(16,15,8,1):
            raise ValueError('Unexpected Bowser baseline')
        for field,value in {6:58,7:1,5:0}.items():
            params.set(row[field],value)
        if separate:
            # Reuse the existing Final Smash UI row; no RF records or strings added.
            from build import edit_database, FIGHTERS
            modified,slot_report=edit_database(raw,[FIGHTERS[0]])
            report['mode']='separate CSS slot, original Bowser unchanged; UI assets not added'
            report['edits']=slot_report
        else:
            modified=bytes(params.data)
        reparsed=Params(modified)
        for i,r in enumerate(params.groups[0]):
            expected=params.values(r)
            if separate:
                if i==60:
                    continue  # Validated by edit_database; inspect exact fields below.
            elif i==16:
                for field,value in {6:58,7:1,5:0}.items():expected[field]=value
            if reparsed.values(reparsed.groups[0][i])!=expected:
                raise ValueError('Unexpected database edit')
        if separate:
            original=Params(raw)
            for i in range(82):
                if i!=60 and original.values(original.groups[0][i])!=reparsed.values(reparsed.groups[0][i]):
                    raise ValueError('Separate-slot probe changed another row')
            slot=reparsed.values(reparsed.groups[0][60])
            if (slot[0],slot[2],slot[6],slot[7],slot[9],slot[13])!=(201,1,58,1,0,52):
                raise ValueError('Incorrect separate slot')
        pack=bytearray(dump.pack(partition,parent))
        original_pack=bytes(pack)
        following=[e.offset for e in resource.entries if e.path.startswith(parent.path) and e.offset>entry.offset]
        boundary=min(following) if following else len(pack)
        blob=zlib.compress(modified,6)
        if len(blob)>boundary-entry.offset:
            raise ValueError('Modified DB exceeds original allocation')
        pack[entry.offset:entry.offset+len(blob)]=blob
        entry.compressed=len(blob)
        encoded=resource.encode()
        checked=Resource(encoded)
        expected=bytearray(original_rf.data)
        expected[entry.table_offset+8:entry.table_offset+12]=len(blob).to_bytes(4,'little')
        if checked.data[128:]!=expected[128:]:raise ValueError('Resource structure changed')
        if len(pack)!=len(original_pack):raise ValueError('Packed archive size changed')
        if pack[:entry.offset]!=original_pack[:entry.offset] or pack[boundary:]!=original_pack[boundary:]:
            raise ValueError('Unrelated packed content changed')
        if zlib.decompress(pack[entry.offset:entry.offset+len(blob)])!=modified:
            raise ValueError('Re-extraction failed')
        (dest/rf_name).write_bytes(encoded)
        file=dest/partition/parent.path/'packed'
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_bytes(pack)
        report['partitions'][partition]={'db_sha256':hashlib.sha256(modified).hexdigest(),'compressed_size':len(blob),'available_span':boundary-entry.offset,'archive_size_unchanged':True,'resource_structure_unchanged':True}
    (dest/'patchlist').write_bytes((dump.patch/'patchlist').read_bytes())
    (out/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'READ-ME.txt').write_text(
        'AROMA GIGA BOWSER FIGHTER-LOAD TEST\n'
        'Copy wiiu to your SD root; select 02-GigaBowser-BowserSlot alone.\n'
        'Select the existing normal Bowser button. Portrait/name remain Bowser.\n'
        'This button loads Giga Bowser (fighter ID 58), with one costume.\n'
        'Normal Mario retains all eight costumes.\n'
        'First test Training on Battlefield: movement and attacks, then exit.\n'
        'Report boot, CSS, match load, actual fighter appearance and training exit.\n'
        'Results/victory are not fixed; avoid a match win for the first test.\n'
        'No extra CSS button yet: this isolates fighter loading from CSS expansion.\n'
        'No resource names/entries, archive offsets or patchlist paths are added.\n'
        'Do not merge with earlier packs. Deselect this pack to restore Bowser.\n',encoding='utf-8')
    if separate:
        (out/'READ-ME.txt').write_text(
            'AROMA TEST 03: SEPARATE GIGA BOWSER SLOT\n'
            'Copy wiiu to SD root. Select 03-GigaBowser-SeparateSlot alone.\n'
            'Normal Bowser is restored. Hidden row 60 is enabled: cosmetic 201, fighter 58, CSS position 52, c00 only.\n'
            'No UI texture files added yet: the new slot may be blank or lack a portrait.\n'
            'Test boot, CSS, presence of the new slot, then Training on Battlefield.\n'
            'If CSS fails or the slot cannot be found, report that; this isolates missing UI from archive reconstruction.\n'
            'If playable, test movement, attacks, one death/respawn, and exiting Training.\n'
            'Respawn persistence and results are unresolved. No engine/script fix is included.\n'
            'All original resource tables, names, entry counts and packed offsets are preserved.\n'
            'Do not merge with earlier packs.\n',encoding='utf-8')
    archive=root/'dist'/(basename+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in out.rglob('*'):
            if file.is_file():z.write(file,file.relative_to(out).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP integrity failure')
    print('Verified all four partitions: only intended roster row changed; original RF structure, archive sizes/offsets and patchlist preserved.')
    print(archive)


if __name__=='__main__':
    main()
