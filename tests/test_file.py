#!/usr/bin/env python3
"""Tests for ``igbpyutils.file``.

Author, Copyright, and License
------------------------------
Copyright (c) 2022-2023 Hauke Daempfling (haukex@zero-g.net)
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
import unittest
from typing import Optional
from unittest.mock import patch
import sys
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from igbpyutils.file import to_Paths, autoglob, Pushd, filetypestr, is_windows_filename_bad, replacer, replace_symlink, NamedTempFileDeleteLater

class TestFileUtils(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_to_paths(self):
        s = __file__
        b = os.fsencode(__file__)
        p = Path(__file__)
        self.assertEqual( (p,), tuple(to_Paths(s)) )
        self.assertEqual( (p,), tuple(to_Paths(b)) )
        self.assertEqual( (p,), tuple(to_Paths(p)) )
        self.assertEqual( (p,p,p), tuple(to_Paths((s,b,p))) )
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            tuple( to_Paths((123,)) )

    def test_autoglob(self):
        testpath = Path(__file__).parent
        testglob = str(testpath/'test_*.py')
        noglob = str(testpath/'zdoesntexist*')
        files = sorted( str(p) for p in testpath.iterdir() if p.name.startswith('test_') and p.name.endswith('.py') )
        self.assertTrue(len(files)>3)
        # this doesn't really test expanduser but that's ok
        self.assertEqual( files+[noglob], sorted(autoglob([testglob, noglob], force=True)) )
        self.assertEqual( files if sys.platform.startswith('win32') else [testglob], list(autoglob([testglob])) )

    def test_pushd(self):
        def realpath(pth):
            if sys.hexversion>=0x030A00F0:  # cover-not-le3.9
                return os.path.realpath(pth, strict=True)
            else:  # cover-not-ge3.10
                return os.path.realpath(pth)
        prevwd = realpath(os.getcwd())
        with (TemporaryDirectory() as td1, TemporaryDirectory() as td2):
            # basic pushd
            with Pushd(td1):
                self.assertEqual(realpath(os.getcwd()), realpath(td1))
                with Pushd(td2):
                    self.assertEqual(realpath(os.getcwd()), realpath(td2))
                self.assertEqual(realpath(os.getcwd()), realpath(td1))
            self.assertEqual(realpath(os.getcwd()), prevwd)
            # exception inside the `with`
            class BogusError(RuntimeError): pass
            with self.assertRaises(BogusError):
                with Pushd(td2):
                    self.assertEqual(realpath(os.getcwd()), realpath(td2))
                    raise BogusError()
            self.assertEqual(realpath(os.getcwd()), prevwd)
            # attempting to change into a nonexistent directory
            with self.assertRaises(FileNotFoundError):
                with Pushd('thisdirectorydoesnotexist'):  # the exception happens here
                    self.fail()  # pragma: no cover
            # attempting to change back to a directory that no longer exists
            with TemporaryDirectory() as td3:
                with self.assertRaises(FileNotFoundError):
                    with Pushd(td3):
                        with Pushd(td2):
                            os.rmdir(td3)
                    # the exception happens here
                    self.fail()  # pragma: no cover

    def test_filetypestr(self):
        with TemporaryDirectory() as td:
            tp = Path(td)
            with open(tp/'foo', 'w', encoding='ASCII') as fh: print("foo", file=fh)
            (tp/'bar').mkdir()
            self.assertEqual( 'regular file', filetypestr( os.lstat(tp/'foo') ) )
            self.assertEqual( 'directory', filetypestr( os.lstat(tp/'bar') ) )
            try:
                (tp/'baz').symlink_to('foo')
            except OSError:  # pragma: no cover
                print(f"Skipping symlink test", file=sys.stderr)
            else:
                self.assertEqual( 'symbolic link', filetypestr( os.lstat(tp/'baz') ) )
            if hasattr(os, 'mkfifo'):
                os.mkfifo(tp/'quz')
                self.assertEqual( 'FIFO (named pipe)', filetypestr( os.lstat(tp/'quz') ) )
            else:  # pragma: no cover
                print("Skipping fifo test", file=sys.stderr)

    def test_is_windows_filename_bad(self):
        self.assertFalse( is_windows_filename_bad("Hello.txt") )
        self.assertFalse( is_windows_filename_bad("Hello .txt") )
        self.assertFalse( is_windows_filename_bad(".Hello.txt") )
        self.assertFalse( is_windows_filename_bad("Héllö.txt") )
        self.assertTrue( is_windows_filename_bad("Hello?.txt") )
        self.assertTrue( is_windows_filename_bad("Hello\tWorld.txt") )
        self.assertTrue( is_windows_filename_bad("Hello\0World.txt") )
        self.assertTrue( is_windows_filename_bad("lpt3") )
        self.assertTrue( is_windows_filename_bad("NUL.txt") )
        self.assertTrue( is_windows_filename_bad("Com1.tar.gz") )
        self.assertTrue( is_windows_filename_bad("Hello.txt ") )
        self.assertTrue( is_windows_filename_bad("Hello.txt.") )

    def test_replacer(self):
        with NamedTempFileDeleteLater('w', encoding='UTF-8') as tf:
            # Basic Test
            print("Hello\nWorld!", file=tf)
            tf.close()
            with replacer(tf.name, encoding='UTF-8') as (ifh, ofh):
                for line in ifh:
                    line = line.replace('o', 'u')
                    print(line, end='', file=ofh)
            self.assertFalse( os.path.exists(ofh.name) )
            with open(tf.name, encoding='UTF-8') as fh:
                self.assertEqual(fh.read(), "Hellu\nWurld!\n")

            # Binary
            with open(tf.name, 'wb') as fh:
                fh.write(b"Hello, World")
            with replacer(tf.name, binary=True) as (ifh, ofh):
                data = ifh.read()
                data = data.replace(b"o", b"u")
                ofh.write(data)
            self.assertFalse( os.path.exists(ofh.name) )
            with open(tf.name, 'rb') as fh:
                self.assertEqual(fh.read(), b"Hellu, Wurld")

            # Failure inside of context
            with self.assertRaises(ProcessLookupError):
                with replacer(tf.name, encoding='UTF-8') as (ifh, ofh):
                    ofh.write("oops")
                    raise ProcessLookupError("blam!")
            self.assertFalse( os.path.exists(ofh.name) )
            with open(tf.name, 'rb') as fh:
                self.assertEqual(fh.read(), b"Hellu, Wurld")

            # Test errors
            with self.assertRaises(TypeError):
                # noinspection PyTypeChecker
                with replacer(bytes()): pass
            with self.assertRaises(ValueError):
                with replacer(Path(tf.name).parent): pass

        # Permissions test
        if not sys.platform.startswith('win32'):
            with NamedTempFileDeleteLater('w', encoding='UTF-8') as tf:
                print("Hello\nWorld!", file=tf)
                tf.close()
                orig_ino = os.stat(tf.name).st_ino
                os.chmod(tf.name, 0o741)
                with replacer(tf.name, encoding='UTF-8') as (_, ofh): pass
                self.assertFalse( os.path.exists(ofh.name) )
                st = os.stat(tf.name)
                self.assertNotEqual( st.st_ino, orig_ino )
                self.assertEqual( stat.S_IMODE(st.st_mode), 0o741 )
        else:   # pragma: no cover
            print(f"Skipping chmod test", file=sys.stderr)

    def test_replace_symlink(self):
        if os.name == 'posix':
            with TemporaryDirectory() as td:
                tp = Path(td)
                fx = tp/'x.txt'
                fy = tp/'y.txt'
                with fx.open('w', encoding='ASCII') as fh: fh.write("Hello, World\n")

                def assert_state(linktarg :str, xtra :Optional[list[Path]]=None):
                    if not xtra: xtra = []
                    self.assertEqual( sorted(tp.iterdir()), sorted([fx,fy]+xtra) )
                    self.assertTrue( fx.is_file() )
                    self.assertTrue( fy.is_symlink() )
                    self.assertEqual( os.readlink(fy), linktarg )

                self.assertEqual( list(tp.iterdir()), [fx] )
                with self.assertRaises(FileNotFoundError):
                    replace_symlink('x.txt', fy)
                self.assertEqual( list(tp.iterdir()), [fx] )

                replace_symlink('x.txt', fy, missing_ok=True)  # create
                assert_state('x.txt')
                replace_symlink('x.txt', fy)  # replace
                assert_state('x.txt')
                replace_symlink(fx, fy)  # replace (slightly different target)
                assert_state(str(fx))

                # test naming collision
                mockf = tp/'.y.txt_1'
                mockf.touch()
                mockcnt = 0
                def mocked_uuid4():
                    nonlocal mockcnt
                    mockcnt += 1
                    return mockcnt  # this is ok because we know it's called as str(uuid.uuid4())
                with patch('igbpyutils.file.uuid.uuid4', new_callable=lambda:mocked_uuid4):
                    replace_symlink(fx, fy)  # abs
                assert_state(str(fx), [mockf])
                mockf.unlink()

                # force an error on os.replace
                fz = tp/'zzz'
                fz.mkdir()
                with self.assertRaises(IsADirectoryError):
                    replace_symlink(fx, fz)
                assert_state(str(fx), [fz])

        else:  # pragma: no cover
            with self.assertRaises(NotImplementedError):
                replace_symlink('/tmp/foo', '/tmp/bar')

    def test_namedtempfiledellater(self):
        with NamedTemporaryFile() as tf1:
            tf1.write(b'Foo')
            tf1.close()
            self.assertFalse( Path(tf1.name).exists() )
        with NamedTempFileDeleteLater() as tf2:
            tf2.write(b'Bar')
            tf2.close()
            self.assertTrue( Path(tf2.name).exists() )
        self.assertFalse( Path(tf2.name).exists() )
        #TODO Later: Once 3.12 is released, change the following to 0x030C00F0
        if sys.hexversion>=0x030C0000:  # cover-not-le3.11
            # noinspection PyArgumentList
            with NamedTemporaryFile(delete=True, delete_on_close=False) as tf3:
                tf3.write(b'Quz')
                tf3.close()
                self.assertTrue( Path(tf3.name).exists() )
            self.assertFalse( Path(tf3.name).exists() )
        else: pass  # cover-not-ge3.12

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
