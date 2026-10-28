"""Build private SDCafiine packs from a user's own US game/update dump."""
import argparse
import copy
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from smash4 import Dump, Entry, Params, Resource, rebuild_resource

TITLE = '0005000010144F00'
DB = 'param/ui/ui_character_db.bin'
FIGHTERS = [
    dict(name='Giga Bowser', id=58, cosmetic=201, row=60, donor=16, asset='Koopag', aliases=['KoopaG'], base='Koopa', module='koopag'),
    dict(name='Wario-Man', id=59, cosmetic=60, row=82, donor=23, asset='Warioman', aliases=[], base='Wario', module='warioman'),
    dict(name='Giga Mac', id=60, cosmetic=202, row=61, donor=39, asset='Littlemacg', aliases=['LittlemacG'], base='Littlemac', module='littlemacg'),
    dict(name='Mega Lucario', id=61, cosmetic=62, row=83, donor=31, asset='LucarioM', aliases=[], base='Lucario', module='lucariom'),
    dict(name='Fighting Mii Brawler', id=62, cosmetic=219, row=73, donor=1, asset='Miienemyf', aliases=['MiiEnemyF'], base='Miifighter', module='miienemyf'),
    dict(name='Fighting Mii Swordfighter', id=63, cosmetic=220, row=74, donor=2, asset='Miienemys', aliases=['MiiEnemyS'], base='Miiswordsman', module='miienemys'),
    dict(name='Fighting Mii Gunner', id=64, cosmetic=221, row=75, donor=3, asset='Miienemyg', aliases=['MiiEnemyG'], base='Miigunner', module='miienemyg'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def edit_database(raw, fighters):
    params = Params(raw)
    if len(params.groups)!=1 or len(params.groups[0])!=82 or len(params.groups[0][0])!=53:
        raise ValueError('Expected unmodified US database: 82 rows of 53 fields')
    rows = params.groups[0]
    # Use reserved Final Smash and enemy rows; append only the two missing forms.
    # Never overwrite Random, All Miis, boss, item, DLC or normal fighter rows.
    expected = {60:(201,0xffffffff),61:(202,0xffffffff),73:(219,62),74:(220,63),75:(221,64)}
    for index,(cosmetic,fighter) in expected.items():
        v=params.values(rows[index])
        if (v[0],v[6],v[2]) != (cosmetic,fighter,0):
            raise ValueError('Reserved row does not match expected original data')
    for donor, fighter in [(16,15),(23,22),(39,41),(31,30),(1,0),(2,1),(3,2)]:
        if params.values(rows[donor])[6] != fighter:
            raise ValueError('Donor fighter does not match expected database')
    # Include the hidden normal Miis in allocation so their positions stay unique.
    nextpos=max(params.values(r)[13] for r in rows if params.values(r)[2] and not params.values(r)[10])+1
    newrows=[]
    for order,f in enumerate(fighters):
        donor=rows[f['donor']]
        begin=donor[0][0]
        end=donor[-1][0]+2
        data=bytearray(raw[begin:end])
        # All 53 fields retain their original type tags and unknown donor values.
        updates={0:f['cosmetic'],1:1,2:1,3:1,5:0,6:f['id'],7:1,9:0,10:0,13:nextpos+order}
        for i in range(21,53):
            updates[i]=1
        for index,value in updates.items():
            pos,kind,_=donor[index]
            from smash4 import FORMATS
            struct.pack_into('>'+FORMATS[kind],data,pos-begin+1,value)
        if f['row']<82:
            target=rows[f['row']]
            params.data[target[0][0]:target[-1][0]+2]=data
        else:
            newrows.append((f['row'],bytes(data)))
    for expected_index,data in sorted(newrows):
        if expected_index != 82+(len(params.data)-len(raw))//127:
            raise ValueError('Unexpected appended row order')
        params.data+=data
    struct.pack_into('>I',params.data,9,82+len(newrows))
    result=bytes(params.data)
    parsed=Params(result)
    changed={f['row'] for f in fighters}
    for i,row in enumerate(rows):
        if i not in changed and params.values(row)!=parsed.values(parsed.groups[0][i]):
            raise ValueError('An unrelated database row changed')
    report=[]
    for order,f in enumerate(fighters):
        report.append({k:f[k] for k in ('name','id','cosmetic','row','module') }|{'css_position':nextpos+order,'costumes':1})
    return result,report


class ArchiveEdits:
    def __init__(self,dump,partition,output):
        self.dump=dump
        self.partition=partition
        self.resource=copy.deepcopy(dump.resources[partition])
        self.output=output
        self.packs={}
        self.additions=[]
        self.replacements={}

    def add(self,path,raw,template=None):
        lookup={e.path:e for e in self.resource.entries}
        existing=lookup.get(path)
        parents=[e for e in self.resource.entries if e.directory and e.flags&0x400 and path.startswith(e.path)]
        parent=max(parents,key=lambda e:len(e.path))
        if parent.path not in self.packs:
            # Metadata in each resource is paired with its own original archive.
            self.packs[parent.path]=bytearray(self.dump.pack(self.partition,parent))
        packed=self.packs[parent.path]
        while len(packed)%128:
            packed.append(0xcc)
        at=len(packed)
        blob=zlib.compress(raw,6)
        packed+=blob
        if existing:
            old_dec=existing.decompressed
            existing.offset,existing.compressed,existing.decompressed=at,len(blob),len(raw)
        else:
            old_dec=0
            depth=len(path.split('/'))
            existing=Entry(-1,-1,path,at,len(blob),len(raw),0x800|depth)
            self.additions.append(existing)
        # Expand every containing directory in this pack. Other files never move.
        for e in self.resource.entries:
            if e.directory and e.path.startswith(parent.path) and path.startswith(e.path):
                e.compressed=max(e.compressed,len(packed)-e.offset)
                e.decompressed=max(e.compressed,e.decompressed+len(raw)-old_dec)
        self.replacements[path]=raw

    def finish(self):
        encoded=rebuild_resource(self.resource,self.additions)
        checked=Resource(encoded)
        before={e.path:e for e in self.resource.entries}
        after={e.path:e for e in checked.entries}
        if set(after)!=set(before)|{e.path for e in self.additions}:
            raise ValueError('Resource rebuild lost entries')
        for path,e in before.items():
            n=after[path]
            if (e.offset,e.compressed,e.decompressed,e.flags)!=(n.offset,n.compressed,n.decompressed,n.flags):
                raise ValueError('Resource metadata round trip failed')
        for path,raw in self.replacements.items():
            e=after[path]
            parent=max((p for p in self.packs if path.startswith(p)),key=len)
            unpacked=zlib.decompress(self.packs[parent][e.offset:e.offset+e.compressed])
            if unpacked!=raw:
                raise ValueError('Repacked content failed verification')
        files=[]
        for parent,data in self.packs.items():
            rel=self.partition+'/'+parent+'packed'
            dest=self.output/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
            files.append(rel)
        name=self.partition.replace('data','resource',1)
        (self.output/name).write_bytes(encoded)
        return files,len(self.additions)


def build(args):
    game=Path(args.game)
    update=Path(args.update)
    for content,title in [(game,TITLE),(update,'0005000E10144F00')]:
        app=ET.parse(content.parent/'code'/'app.xml').getroot()
        if app.findtext('title_id','').upper()!=title:
            raise ValueError('Game/update title ID must be US Smash Wii U')
    dump=Dump(game,update)
    fighters=FIGHTERS[:4] if args.profile=='forms' else FIGHTERS
    for f in fighters:
        model=f"fighter/{f['module']}/model/body/c00/model.nud"
        if not any(e.path==model for e in dump.resources['data'].entries):
            raise ValueError('Missing hidden fighter model: '+f['module'])
    out=Path(args.out)
    if out.exists():
        raise ValueError('Output already exists; choose a fresh output directory')
    packname='HiddenForms-Experimental' if args.profile=='forms' else 'HiddenSeven-Experimental'
    base=out/'sdcafiine'/TITLE/packname/'content'/'patch'
    base.mkdir(parents=True)
    files=[]
    report={'title_id':TITLE,'profile':args.profile,'runtime_tested':False,'partitions':{},'status':'EXPERIMENTAL - hardware validation required'}
    for partition in dump.resources:
        print('Building '+partition,flush=True)
        edits=ArchiveEdits(dump,partition,base)
        raw,_,_=dump.read(partition,DB)
        modified,slots=edit_database(raw,fighters)
        edits.add(DB,modified)
        original_paths={e.path for e in edits.resource.entries}
        for fighter in fighters:
            donor_paths=[e.path for e in edits.resource.entries if e.path.startswith('ui/replace/chr/') and e.path.endswith('_'+fighter['base']+'_01.nut')]
            if not any('/chr_10/' in p for p in donor_paths):
                raise ValueError('Missing donor CSS icon')
            for path in donor_paths:
                for asset in [fighter['asset']]+fighter['aliases']:
                    target=path.replace('_'+fighter['base']+'_01.nut','_'+asset+'_01.nut')
                    if target in original_paths:
                        continue
                    data,_,_=dump.read(partition,path)
                    edits.add(target,data)
        partfiles,added=edits.finish()
        files+=partfiles
        report['partitions'][partition]={'source_db_sha256':sha(raw),'output_db_sha256':sha(modified),'slots':slots,'new_ui_files':added}
    # Existing patchlist records must be retained: the console supplies unchanged files.
    patchlist=bytearray((dump.patch/'patchlist').read_bytes())
    paths={bytes(patchlist[128+i*128:256+i*128]).split(b'\0')[0].decode('ascii') for i in range(struct.unpack_from('<I',patchlist,4)[0])}
    paths.update(files)
    from smash4 import sortkey
    header=patchlist[:128]
    struct.pack_into('<I',header,4,len(paths))
    body=b''.join(p.encode('ascii').ljust(128,b'\0') for p in sorted(paths,key=sortkey))
    (base/'patchlist').write_bytes(header+body)
    report['files']={p.relative_to(out).as_posix():sha(p.read_bytes()) for p in out.rglob('*') if p.is_file()}
    (out/'BUILD-REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'INSTALL.txt').write_text('EXPERIMENTAL: console gameplay/results untested.\nCopy sdcafiine to the SD root for legacy SDCafiine.\nFor Aroma copy the TITLEID directory under wiiu/sdcafiine/.\nSelect this pack alone. Do not combine forms and seven packs.\nUse offline versus/training only. Bosses/items are not playable fighters.\nUI uses donor portraits/names; this does not fix fighter result code.\nDisable the pack to restore the original game.\n',encoding='utf-8')
    print('Built and verified '+str(out),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',required=True,help='Base game content directory')
    parser.add_argument('--update',required=True,help='Matching update content directory')
    parser.add_argument('--profile',choices=['forms','seven'],default='forms')
    parser.add_argument('--out',required=True)
    try:
        build(parser.parse_args())
    except (ValueError,FileNotFoundError) as error:
        parser.exit(1,str(error)+'\n')
