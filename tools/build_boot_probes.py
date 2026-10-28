"""Build Aroma diagnostic packs without regenerating RF directory/name tables."""
import sys
import json
import zlib
from pathlib import Path
from smash4 import Dump, Params, Resource


def main():
    root=Path(__file__).resolve().parents[1]
    dump=Dump(root/'Games/Super Smash Bros/content',root/'Updates/Super Smash Bros/content')
    output=root/'build/aroma-boot-probes-v1'
    if output.exists():
        raise ValueError('Choose a fresh diagnostic output directory')
    for name,probe in [('00-StockControl',False),('01-MarioSevenCostumes',True)]:
        dest=output/'wiiu/sdcafiine/0005000010144F00'/name/'content/patch'
        dest.mkdir(parents=True)
        for partition,resource in dump.resources.items():
            rf_name=partition.replace('data','resource',1)
            raw,entry,parent=dump.read(partition,'param/ui/ui_character_db.bin')
            pack=bytearray(dump.pack(partition,parent))
            if probe:
                params=Params(raw)
                row=params.groups[0][4]
                if params.values(row)[6]!=3 or params.values(row)[7]!=8:
                    raise ValueError('Unexpected Mario baseline')
                params.set(row[7],7)
                changed=bytes(params.data)
                if sum(a!=b for a,b in zip(raw,changed))!=1:
                    raise ValueError('Probe must change exactly one byte')
                blob=zlib.compress(changed,6)
                # Use the existing allocated span; no archive entries move.
                neighbors=[e.offset for e in resource.entries if e.path.startswith(parent.path) and e.offset>entry.offset]
                end=min(neighbors) if neighbors else len(pack)
                if len(blob)>end-entry.offset:
                    raise ValueError('Probe does not fit original allocation')
                pack[entry.offset:entry.offset+len(blob)]=blob
                entry.compressed=len(blob)
                encoded=resource.encode()
                check=Resource(encoded)
                # All structure/name bytes and table indexes stay original.
                expected=bytearray(Resource((dump.patch/rf_name).read_bytes()).data)
                expected[entry.table_offset+8:entry.table_offset+12]=len(blob).to_bytes(4,'little')
                if check.data[128:]!=expected[128:]:
                    raise ValueError('Unexpected RF structural change')
            else:
                encoded=(dump.patch/rf_name).read_bytes()
            (dest/rf_name).write_bytes(encoded)
            packpath=dest/partition/parent.path/'packed'
            packpath.parent.mkdir(parents=True,exist_ok=True)
            packpath.write_bytes(pack)
        # No paths added or removed: preserve patchlist byte for byte.
        (dest/'patchlist').write_bytes((dump.patch/'patchlist').read_bytes())
    (output/'READ-ME.txt').write_text(
        'DIAGNOSTIC PACKS, NOT A HIDDEN-FIGHTER RELEASE.\n'
        'Disable/remove HiddenSeven-Experimental and HiddenForms-Experimental first.\n'
        'Copy wiiu to the SD root. Keep these packs separate; do not merge content.\n'
        'Select 00-StockControl first. If it boots, restart and select 01-MarioSevenCostumes.\n'
        'The second pack only reduces Mario from 8 to 7 costumes; no hidden fighters.\n'
        'Report whether each reaches the title screen and character-select screen.\n'
        'Both use supplied US update metadata (title version 0x0130); installed update must match.\n'
        'If control fails too, compare installed update version and obtain SDCafiine logs.\n',encoding='utf-8')
    print(output)


if __name__=='__main__':
    main()
