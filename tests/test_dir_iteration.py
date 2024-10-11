"""Test various methods to walk a directory tree.

This test does not actually test any functions in this package,
it is simply here to compare different methods to make sure they
all work the same across various versions of Python and OSes and
to see which one is the easiest (and also to see if any
regressions might happen in the future).

Author, Copyright, and License
------------------------------
Copyright (c) 2023-2024 Hauke Daempfling (haukex@zero-g.net)
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, https://www.igb-berlin.de/

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see https://www.gnu.org/licenses/
"""
import os
import sys
import stat
import unittest
import importlib
from enum import Enum
from pathlib import Path
from itertools import chain
from collections import deque
from tempfile import TemporaryDirectory
from more_itertools import only

class FileType(Enum):  # NOTE the names must match those in unzipwalk.FileType!
    FILE = 0
    DIR = 1
    SYMLINK = 2
    OTHER = 3

def path_to_type(p :Path):
    if p.is_symlink():  # cover-not-win32
        return FileType.SYMLINK
    if p.is_dir():
        return FileType.DIR
    if p.is_file():
        return FileType.FILE
    return FileType.OTHER  # cover-not-win32

# b/c `lambda e: raise e` is not valid syntax
def _raise(e):  # pragma: no cover
    raise e

class TestDirIteration(unittest.TestCase):

    tempd_obj :TemporaryDirectory
    td :Path
    expect :list[tuple[str, FileType]]

    @classmethod
    def setUpClass(cls):
        cls.tempd_obj = TemporaryDirectory()  # pylint: disable=consider-using-with
        cls.td = Path(cls.tempd_obj.name)
        (cls.td/'foo').mkdir()
        with (cls.td/'bar.txt').open('w', encoding='ASCII') as fh:
            fh.write("Hello\n")
        with (cls.td/'.quz.txt').open('w', encoding='ASCII') as fh:
            fh.write("World\n")
        with (cls.td/'foo'/'baz.txt').open('w', encoding='ASCII') as fh:
            fh.write("CoOl\n")
        (cls.td/'one'/'two'/'three').mkdir(parents=True)
        with (cls.td/'one'/'two'/'three'/'four.txt').open('w', encoding='ASCII') as fh:
            fh.write("Hi there\n")
        cls.expect = [
            ( str(cls.td/'foo'), FileType.DIR ),
            ( str(cls.td/'bar.txt'), FileType.FILE ),
            ( str(cls.td/'.quz.txt'), FileType.FILE ),
            ( str(cls.td/'foo'/'baz.txt'), FileType.FILE ),
            ( str(cls.td/'one'), FileType.DIR ),
            ( str(cls.td/'one'/'two'), FileType.DIR ),
            ( str(cls.td/'one'/'two'/'three'), FileType.DIR ),
            ( str(cls.td/'one'/'two'/'three'/'four.txt'), FileType.FILE )
        ]
        if not sys.platform.startswith('win32'):  # cover-not-win32  # pragma: no branch
            (cls.td/'foo'/'quz.txt').symlink_to('../.quz.txt')
            (cls.td/'one'/'two'/'three'/'foo').symlink_to('../../../foo')
            os.mkfifo(cls.td/'foo'/'xy.fifo')  # pylint: disable=no-member,useless-suppression  # pyright: ignore [reportAttributeAccessIssue]
            cls.expect.extend([
                ( str(cls.td/'foo'/'quz.txt'), FileType.SYMLINK ),
                ( str(cls.td/'one'/'two'/'three'/'foo'), FileType.SYMLINK ),
                ( str(cls.td/'foo'/'xy.fifo'), FileType.OTHER ),
            ])
        cls.expect.sort()

    @classmethod
    def tearDownClass(cls):
        cls.tempd_obj.cleanup()

    def setUp(self):
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_path_rglob(self):
        """Using ``Path.rglob('*')`` is easiest IMHO."""
        def path_rglobber(path):
            yield from ( (p, path_to_type(p)) for p in Path(path).rglob('*') )
        self.assertEqual(self.expect,
            sorted( (str(p), t) for p,t in path_rglobber(self.td) ) )

    def test_unzipwalk(self):  # pragma: no cover
        """Comparing to our ``unzipwalk`` module (if available) - but this also steps into archives!"""
        try:
            unzipwalk = importlib.import_module('unzipwalk')
        except Exception:
            self.skipTest("unzipwalk could not be loaded")
        else:
            # remap from our FileType to unzipwalk.FileType (by enum name)
            expect = [ (pth, unzipwalk.FileType[typ.name]) for pth,typ in self.expect ]
            self.assertEqual(expect,
                    sorted( (str(only(r.names)), r.typ) for r in unzipwalk.unzipwalk(self.td) ) )

    @unittest.skipIf(sys.hexversion<0x030C00B0, "requires Python 3.12+")
    def test_path_walk(self):  # cover-req-ge3.12
        """Using the new Path.walk() is very similar to os.walk()."""
        def path_walker(path):
            for root, dirs, files in Path(path).walk(on_error=_raise):  # type: ignore[attr-defined, unused-ignore]  # pylint: disable=no-member,useless-suppression  # noqa: E501
                for p in ( root/name for name in chain(dirs, files) ):
                    yield p, path_to_type(p)
        self.assertEqual(self.expect,
            sorted( (str(p), t) for p,t in path_walker(self.td) ) )

    def test_os_walk(self):
        """Using ``os.walk()`` (in combination with ``Path``)."""
        def os_walker(path):
            for root, dirs, files in os.walk(path, onerror=_raise):
                for p in ( Path(root, name) for name in chain(dirs, files) ):
                    yield p, path_to_type(p)
        self.assertEqual(self.expect,
            sorted( (str(p), t) for p,t in os_walker(self.td) ) )

    def test_path_iterdir(self):
        """Using ``Path.iterdir()`` is somewhat manual."""
        def path_iterdirer(path):
            queue = deque( (Path(path),) )
            while len(queue):
                p = queue.popleft()
                if not p.is_symlink() and p.is_dir():
                    queue.extend(p.iterdir())
                if p != path:
                    yield p, path_to_type(p)
        self.assertEqual(self.expect,
            sorted( (str(p), t) for p,t in path_iterdirer(self.td) ) )

    def test_os_scandir(self):
        """Using ``os.scandir()`` is more low-level."""
        def os_scandirer(path):
            queue = deque( (path,) )
            while len(queue):
                with os.scandir(queue.popleft()) as dh:
                    for f in dh:
                        if f.is_symlink():  # cover-not-win32
                            yield f.path, FileType.SYMLINK
                        elif f.is_dir():
                            queue.append(f)
                            yield f.path,FileType.DIR
                        elif f.is_file():
                            yield f.path, FileType.FILE
                        else:  # cover-not-win32
                            yield f.path, FileType.OTHER
        self.assertEqual(self.expect,
            sorted( (p, t) for p,t in os_scandirer(self.td) ) )

    def test_os_listdir(self):
        """Using ``os.listdir()`` is probably the most low-level."""
        def os_listdirer(path):
            queue = deque( (path,) )
            while len(queue):
                d = queue.popleft()
                for fn in os.listdir(d):
                    p = os.path.join(d, fn)
                    mode = os.lstat(p).st_mode
                    if stat.S_ISDIR(mode):
                        yield p, FileType.DIR
                        queue.append(p)
                    elif stat.S_ISREG(mode):
                        yield p, FileType.FILE
                    elif stat.S_ISLNK(mode):  # cover-not-win32
                        yield p, FileType.SYMLINK
                    else:  # cover-not-win32
                        yield p, FileType.OTHER
        self.assertEqual(self.expect,
            sorted( (p, t) for p,t in os_listdirer(self.td) ) )
