"""Prepare an unverified seven-slot candidate for the official exporter.

This deliberately does not claim to fix native respawn/results behavior.
"""
import json
import argparse
import struct
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from smash4 import Dump, Params, owns_pack
from build import FIGHTERS, edit_database


def rpx_sections(path):
    raw=Path(path).read_bytes()
    if raw[:6]!=b'\x7fELF\x01\x02':raise ValueError('Expected Wii U ELF32 big-endian RPX')
    offset=struct.unpack_from('>I',raw,32)[0]
    width,count=struct.unpack_from('>HH',raw,46)
    result=[]
    for i in range(count):
        s=struct.unpack_from('>10I',raw,offset+i*width)
        if s[1] in (0,8) or not s[5]:continue
        data=raw[s[4]:s[4]+s[5]]
        if s[2]&0x08000000:
            expected=struct.unpack_from('>I',data)[0]
            data=zlib.decompress(data[4:])
            if len(data)!=expected:raise ValueError('RPX section length mismatch')
        result.append((s[3],data))
    return result


def cosmetic_map(sections):
    def read(address,count):
        for start,data in sections:
            if start<=address and address+count<=start+len(data):return data[address-start:address-start+count]
        raise ValueError('RPX address is outside a stored section')
    def string(address):
        raw=read(address,40).split(b'\0')[0]
        return raw.decode('ascii')
    # Baseline-specific location, guarded by expected pairs and a sentinel.
    table={}
    for i in range(100):
        key,pointer=struct.unpack('>II',read(0x1033be70+i*8,8))
        if key==0xffffffff:break
        table[key]=string(pointer)
    else:raise ValueError('Missing cosmetic-table sentinel')
    expected={0:'Omakase',16:'Koopa',58:'Kamui',201:'Koopag',202:'Littlemacg',203:'Question',204:'sh_all',219:'Miienemyf'}
    if any(table.get(k)!=v for k,v in expected.items()):raise ValueError('RPX does not match the inspected US v304 cosmetic table')
    return table


def texture_id(raw):
    if raw[:4]!=b'NTWU' or struct.unpack_from('>H',raw,6)[0]!=1:
        raise ValueError('Expected a single-texture Wii U NUT')
    at=raw.find(b'GIDX',16,256)
    if at<0 or struct.unpack_from('>I',raw,at+4)[0]!=16:raise ValueError('Unexpected NUT GIDX layout')
    return at+8,struct.unpack_from('>I',raw,at+8)[0]


def main():
    root=Path(__file__).resolve().parents[1]
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out',default='.private/native-candidate-inputs')
    cli.add_argument('--manifest',default='.private/official-inputs.json')
    cli.add_argument('--report',default='build/native-candidate-report.json')
    args=cli.parse_args()
    output=root/args.out
    if output.exists():raise ValueError('Candidate input directory already exists')
    manifest_path=root/args.manifest
    report_path=root/args.report
    if manifest_path.exists() or report_path.exists():raise ValueError('Manifest and report outputs must be fresh')
    game=root/'Games/Super Smash Bros/content'
    update=root/'Updates/Super Smash Bros/content'
    for content,title in ((game,'0005000010144F00'),(update,'0005000E10144F00')):
        app=ET.parse(content.parent/'code/app.xml').getroot()
        if app.findtext('title_id','').upper()!=title:raise ValueError('US base/update title IDs required')
    if int(ET.parse(update.parent/'code/app.xml').getroot().findtext('title_version'),16)!=304:
        raise ValueError('US update v304 required')
    dump=Dump(game,update)
    if set(dump.resources)!={'data','data(us_en)','data(us_fr)','data(us_sp)'}:raise ValueError('All four US resource partitions required')
    table=cosmetic_map(rpx_sections(update.parent/'code/cross_f.rpx'))
    fighters=[dict(f) for f in FIGHTERS]
    native_paths={e.path for e in dump.resources['data'].entries}
    for f in fighters:
        if 'fighter/'+f['module']+'/model/body/c00/model.nud' not in native_paths:
            raise ValueError('Missing native fighter model: '+f['module'])
        if table.get(f['cosmetic'])!=f['asset']:raise ValueError('Fighter asset/cosmetic mapping mismatch')
    output.mkdir(parents=True)
    # IDs 60/62 are NOT mapped in this executable. Reuse existing placeholder
    # metadata rows with valid hardcoded names rather than inventing mappings.
    manifest=[]
    occupied=set()
    scan_count=0
    # Inspect every native fighter-UI NUT in all US resource partitions.
    for part,resource in dump.resources.items():
        directories={p.path:p for p in resource.entries if p.directory}
        for e in resource.entries:
            if not e.path.startswith('ui/replace/chr/') or not e.path.endswith('.nut'):continue
            parent_path=e.path.rsplit('/',1)[0]+'/'
            while parent_path not in directories or not directories[parent_path].flags&0x400:
                trimmed=parent_path.rstrip('/')
                if '/' not in trimmed:raise ValueError('No native packed ancestor')
                parent_path=trimmed.rsplit('/',1)[0]+'/'
            parent=directories[parent_path]
            physical=part if e.flags&0x800 else 'data'
            pack=dump.pack(physical,parent)
            blob=pack[e.offset:e.offset+e.compressed]
            if blob[:2] in (b'\x78\x9c',b'\x78\xda',b'\x78\x01'):
                head=zlib.decompressobj().decompress(blob,256)
            else:head=blob[:256]
            if head[:4]!=b'NTWU':continue
            if struct.unpack_from('>H',head,6)[0]!=1:
                raise ValueError('Cannot certify unique IDs without a multi-texture parser')
            _,identifier=texture_id(head)
            occupied.add(identifier)
            scan_count+=1
    identifier=0x28fe0000
    seen=set()
    report={'complete':False,'runtime_tested':False,'native_respawn_results_fixed':False,'exporter':'Sm4shExplorer 0.07.4','cosmetic_mappings':{},'roster':[],'native_ui_headers_checked':scan_count,'new_ui':[],'limitations':['Question/sh_all placeholder cosmetic rows repurposed; other menus using these generic cosmetics may show donor artwork.','Portraits/nameplates use ordinary fighter placeholders.','New texture IDs are collision-checked against fighter-UI headers; rendering must be tested.','No RPX or global native mapping patches applied. Respawn/results remain unresolved.']}
    report['shared_ui_aliases_skipped']=0
    for part,resource in dump.resources.items():
        directories={e.path:e for e in resource.entries if e.directory}
        original,_,_=dump.read(part,'param/ui/ui_character_db.bin')
        params=Params(original)
        for index,cosmetic in [(62,203),(63,204)]:
            v=params.values(params.groups[0][index])
            if (v[0],v[6],v[2])!=(cosmetic,0xffffffff,0):raise ValueError('Unexpected placeholder row')
        modified,slots=edit_database(original,fighters)
        if len(Params(modified).groups[0])!=82:raise ValueError('Native roster must retain 82 rows')
        path=output/part/'param/ui/ui_character_db.bin'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(modified)
        manifest.append({'source':str(path),'directory':part+'/param/ui/'})
        report['roster']=slots
        for f in fighters:
            native_name=table[f['cosmetic']]
            report['cosmetic_mappings'][str(f['cosmetic'])]=native_name
            paths=[e.path for e in resource.entries if e.path.startswith('ui/replace/chr/') and e.path.endswith('_'+f['base']+'_01.nut')]
            for donor in paths:
                parent_path=donor.rsplit('/',1)[0]+'/'
                while parent_path not in directories or not directories[parent_path].flags&0x400:
                    trimmed=parent_path.rstrip('/')
                    if '/' not in trimmed:raise ValueError('No native packed ancestor')
                    parent_path=trimmed.rsplit('/',1)[0]+'/'
                # The native folder, not its inherited child records, determines
                # whether a language pack physically exists. Creating a partial
                # language pack for shared UI leaves ordinary-file offsets outside
                # that small pack and fails during CSS bulk loading.
                if not owns_pack(part,directories[parent_path]):
                    report['shared_ui_aliases_skipped']+=1
                    continue
                raw,_,_=dump.read(part,donor)
                at,old_id=texture_id(raw)
                while identifier in occupied:identifier+=1
                new_id=identifier
                occupied.add(new_id)
                identifier+=1
                data=bytearray(raw)
                struct.pack_into('>I',data,at,new_id)
                if data[:at]!=raw[:at] or data[at+4:]!=raw[at+4:]:raise ValueError('Texture pixels/header layout changed')
                target=donor.replace('_'+f['base']+'_01.nut','_'+native_name+'_01.nut')
                key=(part+'/'+target).casefold()
                if key in seen:raise ValueError('Case-insensitive output collision')
                seen.add(key)
                path=output/part/target
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(data)
                manifest.append({'source':str(path),'directory':part+'/'+target.rsplit('/',1)[0]+'/'})
                report['new_ui'].append({'partition':part,'path':target,'old_texture_id':hex(old_id),'new_texture_id':hex(new_id)})
    manifest_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Prepared seven real fighter IDs using seven executable-defined cosmetics, 82 roster rows, one spelling per asset and unique UI IDs.')
    print('Native UI headers inspected:',scan_count,'prepared files:',len(manifest))
    print('Respawn/results are explicitly NOT fixed; this is not a completed release.')


if __name__=='__main__':main()
