"""Small, lossless readers for Smash Wii U resource and parameter files.

Format references: Sammi-Husky/Sm4sh-Tools and Deinonychus71/Sm4shExplorer.
No third party code or game data is bundled.
"""
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


@dataclass
class Entry:
    index: int
    table_offset: int
    path: str
    offset: int
    compressed: int
    decompressed: int
    flags: int

    @property
    def directory(self):
        return bool(self.flags & 0x200)


def owns_pack(partition, parent):
    """Physical ownership comes from the packed folder, not child flags.

    Native language RF tables can set 0x800 on inherited children even when
    the enclosing folder is shared. Do not synthesize partial language packs.
    """
    if not parent.directory or not parent.flags&0x400:
        raise ValueError('A packed folder record is required')
    return partition=='data' or bool(parent.flags&0x800)


class Resource:
    def __init__(self, data):
        if data[:2] != b'RF':
            raise ValueError('Not a Smash Wii U resource file')
        self.header = bytearray(data[:128])
        self.data = bytearray(data[:128] + zlib.decompress(data[128:]))
        if len(self.data) - 128 != u32(data, 28):
            raise ValueError('Resource decompressed size mismatch')
        strings = u32(data, 32)
        extpos = strings + u32(self.data, strings) * 0x2000 + 4
        extcount = u32(self.data, extpos)

        def string(offset):
            start = strings + 4 + offset
            return bytes(self.data[start:self.data.index(0, start)]).decode('ascii')

        extensions = [string(u32(self.data, extpos + 4 + 4*i)) for i in range(extcount)]
        pos = u32(data, 12)
        pos += u32(self.data, pos) * 8 + 4
        pos += u32(self.data, pos) + 4
        self.entries = []
        parts = []
        for i in range(u32(data, 40)):
            at = pos + i * 24
            off, namebits, cmp, dec, timestamp, flags = struct.unpack_from('<6I', self.data, at)
            if off == 0xbbbbbbbb:
                continue
            nameoff = namebits & 0xfffff
            if namebits & 0x800000:
                ref = struct.unpack_from('<H', self.data, strings + 4 + nameoff)[0]
                length = (ref & 31) + 4
                distance = ((ref & 0xe0) >> 6 << 8) | (ref >> 8)
                name = string(nameoff - distance)[:length] + string(nameoff + 2)
            else:
                name = string(nameoff)
            name += extensions[namebits >> 24]
            if not name or flags & 0x2000:
                continue
            depth = flags & 255
            if not 1 <= depth <= len(parts) + 1:
                raise ValueError('Invalid resource folder depth')
            parts = parts[:depth-1] + [name]
            self.entries.append(Entry(i, at, ''.join(parts), off, cmp, dec, flags))

    def encode(self):
        for e in self.entries:
            struct.pack_into('<I', self.data, e.table_offset, e.offset)
            struct.pack_into('<II', self.data, e.table_offset + 8, e.compressed, e.decompressed)
        body = zlib.compress(self.data[128:], 9)
        header = bytearray(self.header)
        struct.pack_into('<II', header, 24, len(body), len(self.data)-128)
        return bytes(header) + body


FORMATS = {1:'B', 2:'b', 3:'H', 4:'h', 5:'I', 6:'i', 7:'f'}


class Params:
    def __init__(self, data):
        self.data = bytearray(data)
        if data[:4] != b'\xff\xff\0\0':
            raise ValueError('Unexpected parameter header')
        pos = 8
        self.groups = []
        group = []
        width = None
        while pos < len(data):
            kind = data[pos]
            if kind == 0x20:
                if width is not None:
                    self._group(group, width)
                elif group:
                    self.groups.append([group])
                width = struct.unpack_from('>I', data, pos+1)[0]
                group = []
                pos += 5
            elif kind in FORMATS:
                fmt = '>' + FORMATS[kind]
                group.append((pos, kind, struct.unpack_from(fmt, data, pos+1)[0]))
                pos += 1 + struct.calcsize(fmt)
            elif kind == 8:
                size = struct.unpack_from('>I', data, pos+1)[0]
                group.append((pos, kind, data[pos+5:pos+5+size].decode('ascii')))
                pos += 5 + size
            else:
                raise ValueError(f'Unknown parameter type {kind} at {pos}')
        if width is not None:
            self._group(group, width)
        elif group:
            self.groups.append([group])

    def _group(self, group, width):
        # The group word is the number of STRUCTS, not fields per struct.
        if not width or len(group) % width:
            raise ValueError('Invalid parameter group')
        fields = len(group)//width
        self.groups.append([group[i*fields:(i+1)*fields] for i in range(width)])

    def set(self, field, value):
        pos, kind, _ = field
        struct.pack_into('>' + FORMATS[kind], self.data, pos+1, value)

    def values(self, row):
        return [v for _, _, v in row]


def extract(patch, resource, path, partition='data'):
    entry = next(e for e in resource.entries if e.path == path)
    ancestors = [e for e in resource.entries if e.directory and e.flags & 0x400 and path.startswith(e.path)]
    parent = max(ancestors, key=lambda e: len(e.path))
    pack = (Path(patch) / (partition + '/' + parent.path + 'packed')).read_bytes()
    blob = pack[entry.offset:entry.offset+entry.compressed]
    raw = zlib.decompress(blob) if entry.compressed != entry.decompressed else blob
    if len(raw) != entry.decompressed:
        raise ValueError('Packed entry size mismatch')
    return raw, entry, parent


def sortkey(path):
    return path.replace('/', '\0')


def rebuild_resource(resource, additions=()):
    """Rebuild directory/name tables following Sm4shExplorer's RF layout.

    Existing names, offsets, flags and timestamps are preserved. New names go
    into one additional 0x2000 string block; no original name refs are moved.
    """
    strings = u32(resource.header, 32)
    oldblocks = u32(resource.data, strings)
    extpos = strings + oldblocks * 0x2000 + 4
    extension_count = u32(resource.data, extpos)
    name_table = bytearray(resource.data[strings:extpos])
    new_names = bytearray()
    namebits = {e.path:u32(resource.data, e.table_offset+4) for e in resource.entries}
    timestamps = {e.path:u32(resource.data, e.table_offset+16) for e in resource.entries}
    for entry in additions:
        if entry.path in namebits:
            raise ValueError('Cannot add an existing resource')
        name = entry.path.rstrip('/').rsplit('/', 1)[-1]
        if entry.directory:
            name += '/'
            ext = 0
        else:
            suffix = Path(name).suffix
            ext = None
            for i in range(extension_count):
                offset = u32(resource.data, extpos+4+i*4)
                start = strings+4+offset
                text = bytes(resource.data[start:resource.data.index(0,start)]).decode('ascii')
                if text == suffix:
                    ext = i
                    break
            if ext is None:
                raise ValueError('Unknown resource extension')
            name = name[:-len(suffix)] if suffix else name
        at = oldblocks*0x2000+len(new_names)
        if at >= 0x100000:
            raise ValueError('Resource name offset overflow')
        namebits[entry.path] = (ext << 24) | at
        new_names += name.encode('ascii')+b'\0'
    if len(new_names) > 0x2000:
        raise ValueError('New resource names exceed reserved block')
    if additions:
        name_table += new_names + bytes(0x2000-len(new_names))
        struct.pack_into('<I', name_table, 0, oldblocks+1)
    name_table += resource.data[extpos:extpos+4+4*extension_count]
    entries = sorted(resource.entries+list(additions), key=lambda e:sortkey(e.path))
    table = bytearray(24)
    table[4] = 0x10
    table[21] = 2
    for e in entries:
        table += struct.pack('<6I',e.offset,namebits[e.path],e.compressed,e.decompressed,timestamps.get(e.path,0),e.flags)
    resource_size = len(table)
    while len(table)%16 or len(table)<resource_size+32:
        table.append(0xbb)
    header = bytearray(resource.header)
    struct.pack_into('<I',header,12,128)
    struct.pack_into('<I',header,16,resource_size)
    struct.pack_into('<III',header,32,len(table)+128,len(name_table),len(entries)+1)
    body = table+name_table
    original_size = len(body)
    while len(body)%16 or len(body)<original_size+96:
        body.append(0xbb)
    compressed = zlib.compress(body,6)
    struct.pack_into('<II',header,24,len(compressed),len(body))
    return bytes(header)+compressed


class Dump:
    def __init__(self, game, update):
        self.game = Path(game)
        self.patch = Path(update)/'patch'
        ls = (self.game/'ls').read_bytes()
        if ls[:4] != b'of\x02\0':
            raise ValueError('Expected Wii U LS v2')
        self.ls = {}
        for i in range(u32(ls,4)):
            crc,offset,size,dt,padding = struct.unpack_from('<IIIHH',ls,8+i*16)
            self.ls[crc] = offset,size,dt
        self.cache = {}
        self.resources = {f.name.replace('resource','data',1):Resource(f.read_bytes()) for f in self.patch.glob('resource*')}

    def pack(self, partition, parent):
        path = partition+'/'+parent.path+'packed'
        if path not in self.cache:
            file = self.patch/path
            if file.is_file():
                data = file.read_bytes()
            else:
                b = bytearray(path.encode('ascii'))
                for i in range(4):
                    b[i] ^= 255
                crc = zlib.crc32(b)
                if crc not in self.ls:
                    if partition != 'data':
                        return self.pack('data',parent)
                    raise ValueError('Packed archive not found: '+path)
                offset,size,dt = self.ls[crc]
                with (self.game/f'dt{dt:02d}').open('rb') as stream:
                    stream.seek(offset)
                    data = stream.read(size)
            self.cache[path] = data
        return self.cache[path]

    def read(self, partition, path):
        resource = self.resources[partition]
        entry = next(e for e in resource.entries if e.path==path)
        parents = [e for e in resource.entries if e.directory and e.flags&0x400 and path.startswith(e.path)]
        parent = max(parents,key=lambda e:len(e.path))
        physical = partition if entry.flags&0x800 else 'data'
        pack = self.pack(physical,parent)
        blob = pack[entry.offset:entry.offset+entry.compressed]
        raw = zlib.decompress(blob) if blob[:2] in (b'\x78\x9c',b'\x78\xda',b'\x78\x01') else blob
        if len(raw)!=entry.decompressed:
            raise ValueError('Invalid extracted size: '+partition+'/'+path)
        return raw,entry,parent
