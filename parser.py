#!/usr/bin/env python3
# -*- mode: python -*-


# published by Enzo Salson


import datetime
from optparse import OptionParser
import os.path
import struct
import sys
import time

NAMES = {
    "vmhd": "video information media header",
    "mvhd": 'movie header',
    "tkhd": 'track header',
    "mdhd": 'media header',
    "smhd": 'sound media information header', 
    "hdlr": 'handler reference',

    "stsd": "sample description", 
    "stts": "time-to-sample", 
    "stsc": "sample-to-chunk", 
    "stco": 'chunk offset', 
    "stsz": 'sample size', 
    "ctts": 'composition offset', 
    "stss": "sync sample", 
}

CONTAINER_ATOMS = ["moov", "trak", "mdia", "minf","dinf","stbl"]
_IGNORE_ATOMS = ["iods"] 
_ATOMS = {
    "pnot": (12, "I2x4s2x",
             ("Modification time", "Atom type"),
             (0,)),
    "vmhd": (12, "4xH6x",
             ("graphics mode",),
             () ),
    "mvhd": (100, "4x5IH10x36x7I",
             ("Creation time", "Modification time",
              "Time Scale",
              'Duration',
              'Preferred rate',
              'Preferred volume',
              'preview time',
              'preview duration',
              'poster time',
              'selection time',
              'selection duration',
              'current time',
              'next track id'
              ),
             (4, 8)),
    "tkhd": (84, "4x2I72x",
             ("Creation time", "Modification time"),
             (4, 8)),
    "mdhd": (24, "B3x4I2H", 
             ("Version", "Creation time", "Modification time","Time Scale","Duration","Language","Quality"),
             (4, 8)), 
    "smhd": (8, "4xH2x",
             ("balance",),
             ())
}

_VARIABLE_LEN_ATOMS = {
    "hdlr": (4 + 5*4, "4x5I",
             ("Component type",
              'component subtype',
              'component manufacturer',
              'component flags',
              'component flags mask'),
             (),
             "component name"
             ),
    "stsd": (8, "4xI",
             ("number of entries",),
             (),
             "sample description table"),
    "stts": (8,"4xI",
             ("number of entries",),
             (),
             "time-to-sample table"),
    "stsc": (8,"4xI",
             ("number of entries",),
             (),
             "sample-to-chunk table"),
    "stco": (8,"4xI",
             ("number of entries",),
             (),
             "chunk offset table"),
    "stsz": (12,"4xII",
             ("sample size","number of entries",),
             (),
             "sample size table"),
    "ctts": (12,"4xII",
             ("entry count",),
             (),
             "composition offset table"),
    "stss": (12,"4xII",
             ("number of entries",),
             (),
             "sync sample table")
    

}

_VARIABLE_CHAINED_ATOMS = {
    "dref": (8, "4xI",
             ("number of entries",),
             (),
             "data references"
             )
}

_DATES = ("Creation time", "Modification time")

class Mov(object):
    def __init__(self, fn):
        self._fn = fn
        self._offsets = []

    def parse(self):
        fsize = os.path.getsize(self._fn)
        print("File: {} ({} bytes, {} MB)".format(self._fn, fsize, fsize / (1024.**2)))
        with open(self._fn, "rb") as self._f:
            self._parse(fsize)

    def _f_read(self,l):
        print('reading '+str(l))
        return self._f.read(l)

    def _parse(self, length, depth=0):
        prefix = "  "*depth + "- "
        n = 0
        while n < length:
            data = self._f_read(8)
            #print(len(data), data)
            al, an = struct.unpack(">I4s", data)
            an = an.decode()
            print("{}Atom: {} ({} bytes)".format(prefix, an, al))

            if an in _ATOMS:
                self._parse_atom(an, al-8, depth)
            elif an == "udta":
                self._parse_udta(al-8, depth)
            elif an == "ftyp":
                self._read_ftyp(al-8, depth)
            elif an in CONTAINER_ATOMS:
                self._parse(al-8, depth+1)
            elif an in _VARIABLE_LEN_ATOMS:
                self._parse_atom(an, al-8, depth, variable=True)
            elif an in _VARIABLE_CHAINED_ATOMS:
                self._parse_atom(an, al-8, depth, chained=True)
            elif an in _IGNORE_ATOMS:
                self._f_read(al-8)
            else:
                print('unhandled thingie',al,an)
                if al == 1:
                    print("64 bit header!")
                    al = struct.unpack(">Q", self._f_read(8))[0]
                    self._f_read(al-16)
                else:
                    self._f_read(al-8)
            n += al

    def _parse_atom(self, atom, length, depth, variable=False, chained=False):
        if variable:
            spec = _VARIABLE_LEN_ATOMS[atom]
        elif chained:
            spec = _VARIABLE_CHAINED_ATOMS[atom]
        else:
            spec = _ATOMS[atom]
            assert length == spec[0]
            
        pos = self._f.tell()
        prefix = "  "*depth + "  | "
        data = self._f_read(length)
        if variable:
            v = struct.unpack(">"+spec[1], data[:spec[0]])
        elif chained:
            v = struct.unpack(">"+spec[1], data[:spec[0]])
        else:
            v = struct.unpack(">"+spec[1], data)
        k = spec[2]
        for i in range(len(k)):
            vv = v[i]
            if type(vv) == bytes:
                vv = vv.decode()
            elif k[i] in _DATES:
                vv = self._macdate2date(vv)
            print("{}{}: {}".format(prefix, k[i], vv))

        if variable or chained:
            lim = 10
            realdata = data[spec[0]:]
            if len(realdata) > lim:
                print("{}{}: {}{}{}{}".format(prefix, spec[4], realdata[:lim], '...', len(realdata)-lim,' more bytes'))
            else:
                print("{}{}: {}".format(prefix, spec[4], realdata))

        for offset in spec[3]:
            self._offsets.append(pos + offset)

    def _read_ftyp(self, length, depth):
        prefix = "  "*depth + "  | "
        data = self._f_read(8)
        brand, version = struct.unpack(">4sI", data)
        brand = brand.decode("latin1")
        print("{}Brand: {}, version: {}".format(prefix, brand, version))
        self._f_read(length-8)

    def _parse_udta(self, length, depth):
        prefix = "  "*depth + "  | "
        n = 0
        while n < length:
            atom_size, data_type = struct.unpack(">I4s", self._f_read(8))
            data_type = data_type.decode("latin1")
            raw = self._f_read(atom_size-8)
            if data_type[0] == "©":
                print("{}{}: {}".format(prefix, data_type, raw[3:].decode()))
            else:
                print("{}{} ({} bytes)".format(prefix, data_type, atom_size-8))
            n += atom_size

    def _macdate2date(self, md):
        d = datetime.datetime(1904, 1, 1) + datetime.timedelta(seconds=md)
        return "{} ({})".format(d, md)

    def _date2macdate(self, d):
        td = datetime.datetime(1970, 1, 1) - datetime.datetime(1904, 1, 1)
        dd = d + td
        sec = time.mktime(dd.timetuple()) - time.timezone
        return int(sec)

    def set_date(self, d):
        md = self._date2macdate(d)
        print("New date: {} ({})".format(d, md))
        with open(self._fn, "r+b") as f:
            print("Writing new date at {} positions...".format(len(self._offsets)))
            for offset in self._offsets:
                f.seek(offset)
                data = struct.pack(">I", md)
                f.write(data)
            f.flush()
            print("Touching file...")
            ts = time.mktime(d.timetuple())
            os.utime(self._fn, (ts, ts))
        print("Done! :)")

if __name__ == "__main__":
    usage = "Usage: %prog [options] file.mov [\"YYYY-MM-DD hh:mm:ss\"]"
    parser = OptionParser(usage)
    
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("Number of arguments are incrorrects.")
        
    m = Mov(args[0])
    m.parse()

    if len(args) > 1:
        d = datetime.datetime.strptime(args[1], "%Y-%m-%d %H:%M:%S")
        m.set_date(d)
