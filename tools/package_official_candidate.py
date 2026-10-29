"""Package a verified official export for private Aroma SDCafiine testing."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--patch',required=True)
    cli.add_argument('--verification',default='build/official-verification.json')
    cli.add_argument('--out',default='build/aroma-native-seven-candidate-v2')
    cli.add_argument('--pack-name',default='07-HiddenSeven-SharedUI')
    args=cli.parse_args()
    if not args.pack_name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.pack_name):
        raise ValueError('Pack name must contain only letters, digits, hyphens and underscores')
    patch=Path(args.patch)
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/args.verification).read_text(encoding='utf-8'))
    if not report.get('archive_validation_passed') or report.get('validation_schema')!=2 or not report.get('physical_partition_layout_verified'):
        raise ValueError('Current archive and physical-partition validation required; legacy reports are insufficient')
    files={p.relative_to(patch).as_posix():p for p in patch.rglob('*') if p.is_file()}
    if files.keys()!=report['files'].keys():raise ValueError('Verified export file set differs')
    for name,path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=report['files'][name]:raise ValueError('Export changed since verification')
    out=root/args.out
    if out.exists():raise ValueError('Output directory must be fresh')
    archive=root/'dist'/f'{out.name}.zip'
    if archive.exists():raise ValueError('ZIP already exists')
    destination=out/'wiiu/sdcafiine/0005000010144F00'/args.pack_name/'content/patch'
    shutil.copytree(patch,destination)
    (out/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (out/'README.txt').write_text('US v304 / Aroma SDCafiine / experimental '+args.pack_name+'\n\nCopy wiiu to the SD root. Select only '+args.pack_name+'. Do not merge with older packs.\n\nArchive contents verified; runtime stability NOT verified. Not a complete stable release.\nShared UI is imported only into its native physical partition, avoiding partial language packs.\nSeven slots use existing rows and executable-defined cosmetic names.\nArtwork and nameplates are ordinary-fighter placeholders. Question/sh_all cosmetic reuse may affect other menus.\nRespawn reversion and results crashes remain unresolved. Training-only investigation recommended; avoid results testing until these are fixed.\nKeep this generated game-data package private. Public repository contains source only.\n',encoding='utf-8')
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        for file in sorted(out.rglob('*')):
            if file.is_file():zipped.write(file,file.relative_to(out).as_posix())
    with zipfile.ZipFile(archive) as zipped:
        prefix=destination.relative_to(out).as_posix()+'/'
        for name,digest in report['files'].items():
            if hashlib.sha256(zipped.read(prefix+name)).hexdigest()!=digest:
                raise ValueError('ZIP member differs from verified export')
    print('Packaged '+args.pack_name+'; archive verified, gameplay unverified. Not a stable release.')


if __name__=='__main__':main()
