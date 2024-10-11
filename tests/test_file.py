"""Tests for ``igbpyutils.file``.

Author, Copyright, and License
------------------------------
Copyright (c) 2022-2024 Hauke Daempfling (haukex@zero-g.net)
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
import io
import os
import sys
import stat
import unittest
import warnings
from pathlib import Path
from typing import Optional
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout
from tempfile import TemporaryDirectory, NamedTemporaryFile
from igbpyutils.file import (to_Paths, autoglob, Pushd, filetypestr, is_windows_filename_bad, replacer, replace_symlink, replace_link,
                             NamedTempFileDeleteLater, simple_perms, cmdline_rglob, simple_cache, open_out)

class TestFileUtils(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_to_paths(self):
        s = __file__
        b = os.fsencode(__file__)
        p = Path(__file__)
        self.assertEqual( (p,), tuple(to_Paths(s)) )
        self.assertEqual( (p,), tuple(to_Paths(b)) )
        self.assertEqual( (p,), tuple(to_Paths(p)) )
        self.assertEqual( (p,p,p), tuple(to_Paths((s,b,p))) )
        with self.assertRaises(TypeError):
            tuple( to_Paths((123,)) )  # type: ignore[arg-type]

    def test_autoglob(self):
        testpath = Path(__file__).parent
        testglob = str(testpath/'test_*.py')
        noglob = str(testpath/'zdoesntexist*')
        files = sorted( str(p) for p in testpath.iterdir() if p.name.startswith('test_') and p.name.endswith('.py') )
        self.assertTrue(len(files)>3)
        # this doesn't really test expanduser but that's ok
        orig_shell = os.environ.get('SHELL', None)
        orig_comsp = os.environ.get('COMSPEC', None)
        try:
            # Windows cmd.exe:
            os.environ.pop('SHELL', None)
            os.environ['COMSPEC'] = r'C:\WINDOWS\system32\cmd.exe'
            self.assertEqual( files, sorted(autoglob([testglob])) )
            self.assertEqual( files+[noglob], sorted(autoglob([testglob, noglob], force=True)) )

            # Windows Git Bash:
            os.environ['SHELL'] = r'C:\Users\nobody\AppData\Local\Programs\Git\usr\bin\bash.exe'
            os.environ['COMSPEC'] = r'C:\WINDOWS\system32\cmd.exe'
            self.assertEqual( [testglob], list(autoglob([testglob])) )
            self.assertEqual( files+[noglob], sorted(autoglob([testglob, noglob], force=True)) )

            # Linux:
            os.environ['SHELL'] = r'/bin/bash'
            os.environ.pop('COMSPEC', None)
            self.assertEqual( [testglob], list(autoglob([testglob])) )
            self.assertEqual( files+[noglob], sorted(autoglob([testglob, noglob], force=True)) )

        # coverage disabled because we don't know what the state of the environment was:
        finally:  # pragma: no cover
            if orig_shell is None:
                os.environ.pop('SHELL', None)
            else:
                os.environ['SHELL'] = orig_shell
            if orig_comsp is None:
                os.environ.pop('COMSPEC', None)
            else:
                os.environ['COMSPEC'] = orig_comsp

    def test_cmdline_rglob(self):
        iswin = sys.platform.startswith('win32')
        with (TemporaryDirectory() as tempdir, NamedTempFileDeleteLater(suffix='.txt') as tempf):
            tempf.close()
            td = Path(tempdir).resolve(strict=True)
            # we want the tempf to be outside the tempdir
            self.assertFalse( Path(tempf.name).resolve(strict=True).is_relative_to(td) )
            (td/'foo').mkdir()
            (td/'one.txt').touch()
            (td/'.two.txt').touch()
            (td/'foo'/'three.txt').touch()
            if not iswin:  # cover-not-win32  # pragma: no branch
                (td/'bar').symlink_to('foo')
                (td/'outside').symlink_to(tempf.name)
                (td/'foo'/'.link.txt').symlink_to('../.two.txt')
                (td/'foo'/'broken.txt').symlink_to('../does_not_exist')
            with Pushd(td):
                self.assertEqual( sorted([ td, td/'foo', td/'one.txt', td/'.two.txt', td/'foo'/'three.txt' ]
                    + ([] if iswin else [ td/'bar', td/'outside', td/'foo'/'.link.txt', td/'foo'/'broken.txt' ])),
                    sorted( cmdline_rglob(td) ) )
                self.assertEqual( sorted([ td/'foo', td/'one.txt', td/'foo'/'three.txt' ]
                    + ([] if iswin else [ td/'foo'/'.link.txt', td/'foo'/'broken.txt' ])),
                    sorted( cmdline_rglob([td/'foo', td/'one.txt']) ))
                self.assertEqual( sorted([ td/'foo'/'three.txt' ]
                    + ([] if iswin else [ td/'foo'/'broken.txt' ])),
                    sorted( cmdline_rglob(autoglob([str(td/'foo'/'*')], force=True)) ))
                self.assertEqual( sorted([ Path('foo'), Path('one.txt'), Path('.two.txt'), Path('foo','three.txt') ]
                    + ([] if iswin else [ Path('bar'), Path('outside'), Path('foo','.link.txt'), Path('foo','broken.txt') ])),
                    sorted( cmdline_rglob([]) ))
                # empty generator (like autoglob) should be same as empty list
                def empty_gen():
                    yield from ()
                self.assertEqual( sorted( cmdline_rglob([]) ), sorted( cmdline_rglob(empty_gen()) ) )
                # Use a simpler test for the duplicate detection, because we can't be sure of the directory structure on the test runner
                self.assertEqual( [td/'one.txt'], list(cmdline_rglob([td/'one.txt', 'one.txt'])) )
                #self.assertEqual( sorted([ Path('foo'), Path('foo','three.txt'), td, td/'one.txt', td/'.two.txt' ]
                #    + ([] if iswin else [ Path('foo','.link.txt'), Path('foo','broken.txt'), td/'bar', td/'outside' ])),
                #    sorted( cmdline_rglob(['foo', td]) ))

    def test_pushd(self):
        def realpath(pth):
            if sys.hexversion>=0x030A00B0:  # cover-req-ge3.10
                return os.path.realpath(pth, strict=True)  # type: ignore[call-overload, unused-ignore]
            return os.path.realpath(pth)  # cover-req-lt3.10
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
            class BogusError(RuntimeError):
                pass
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
            with open(tp/'foo', 'w', encoding='ASCII') as fh:
                print("foo", file=fh)
            (tp/'bar').mkdir()
            self.assertEqual( 'regular file', filetypestr( os.lstat(tp/'foo') ) )
            self.assertEqual( 'directory', filetypestr( os.lstat(tp/'bar') ) )
            if not sys.platform.startswith('win32'):  # cover-not-win32
                (tp/'baz').symlink_to('foo')
                self.assertEqual( 'symbolic link', filetypestr( os.lstat(tp/'baz') ) )
                os.mkfifo(tp/'quz')  # pylint: disable=no-member,useless-suppression  # pyright: ignore [reportAttributeAccessIssue]
                self.assertEqual( 'FIFO (named pipe)', filetypestr( os.lstat(tp/'quz') ) )
            else:  # cover-only-win32
                print("skip-symlink-fifo", end='.', file=sys.stderr)

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
                with replacer(bytes()):  # type: ignore[arg-type]
                    pass  # pragma: no cover
            with self.assertRaises(ValueError):
                with replacer(Path(tf.name).parent):
                    pass  # pragma: no cover

        # Permissions test
        if not sys.platform.startswith('win32'):  # cover-not-win32
            with NamedTempFileDeleteLater('w', encoding='UTF-8') as tf:
                print("Hello\nWorld!", file=tf)
                tf.close()
                orig_ino = os.stat(tf.name).st_ino
                os.chmod(tf.name, 0o741)
                with replacer(tf.name, encoding='UTF-8') as (_, ofh):
                    pass
                self.assertFalse( os.path.exists(ofh.name) )
                st = os.stat(tf.name)
                self.assertNotEqual( st.st_ino, orig_ino )
                self.assertEqual( stat.S_IMODE(st.st_mode), 0o741 )
        else:   # cover-only-win32
            print("skip-chmod", end='.', file=sys.stderr)

    @unittest.skipIf(condition=os.name!='posix', reason='only on POSIX')
    def test_replace_symlink(self):  # cover-only-posix
        with TemporaryDirectory() as td:
            tp = Path(td)
            fx = tp/'x.txt'
            fy = tp/'y.txt'
            with fx.open('w', encoding='ASCII') as fh:
                fh.write("Hello, World\n")

            def assert_state(linktarg :str, xtra :Optional[list[Path]]=None):
                if not xtra:
                    xtra = []
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
            self.assertEqual(mockcnt, 2)
            assert_state(str(fx), [mockf])
            mockf.unlink()

            # force an error on os.replace
            fz = tp/'zzz'
            fz.mkdir()
            with self.assertRaises(IsADirectoryError):
                replace_symlink(fx, fz)
            assert_state(str(fx), [fz])

    @unittest.skipIf(condition=os.name=='posix', reason='not on POSIX')
    def test_replace_link_nonposix(self):  # cover-not-posix
        with self.assertRaises(NotImplementedError):
            replace_symlink('/tmp/foo', '/tmp/bar')
        with self.assertRaises(NotImplementedError):
            replace_link('/tmp/foo', '/tmp/bar')

    @unittest.skipIf(condition=os.name!='posix', reason='only on POSIX')
    def test_replace_link(self):  # cover-only-posix

        def assert_hardlink(a :Path, b:Path):
            self.assertTrue( a.is_file() )
            self.assertTrue( b.is_file() )
            ast = a.lstat()
            bst = b.lstat()
            self.assertEqual(ast.st_dev,  bst.st_dev)
            self.assertEqual(ast.st_ino,  bst.st_ino)
            self.assertEqual(ast.st_mode, bst.st_mode)
            self.assertEqual(ast.st_uid,  bst.st_uid)
            self.assertEqual(ast.st_gid,  bst.st_gid)
            self.assertEqual(ast.st_nlink, 2)
            self.assertEqual(bst.st_nlink, 2)

        def assert_symlink(f :Path, ln: Path, t :str):
            self.assertTrue( f.is_file() )
            self.assertTrue( ln.is_symlink() )
            self.assertEqual( os.readlink(ln), t )
            self.assertEqual( f.resolve(strict=True), ln.resolve(strict=True) )

        with TemporaryDirectory() as td:
            tp = Path(td)
            fx = tp/'x.txt'
            fy = tp/'y.txt'
            fz = tp/'z.txt'
            with fx.open('w', encoding='ASCII') as fh:
                fh.write("Hello, World\n")
            with fz.open('w', encoding='ASCII') as fh:
                fh.write("Testing 123\n")
            self.assertEqual( sorted(tp.iterdir()), [fx, fz] )

            replace_link(fx, fy)  # create
            self.assertEqual( sorted(tp.iterdir()), [fx, fy, fz] )
            assert_hardlink(fx, fy)

            replace_link(fx, fy)  # replace
            self.assertEqual( sorted(tp.iterdir()), [fx, fy, fz] )
            assert_hardlink(fx, fy)

            replace_link(fz, fy)  # replace with other
            self.assertEqual( sorted(tp.iterdir()), [fx, fy, fz] )
            assert_hardlink(fz, fy)
            self.assertEqual( fx.lstat().st_nlink, 1 )

            # force an error on os.replace
            fd = tp/'ddd'
            fd.mkdir()
            with self.assertRaises(IsADirectoryError):
                replace_link(fx, fd)
            self.assertEqual( sorted(tp.iterdir()), [fd, fx, fy, fz] )

            # now do symbolic links
            fd.rmdir()
            fy.unlink()
            self.assertEqual( sorted(tp.iterdir()), [fx, fz] )

            replace_link('x.txt', fy, symbolic=True)  # create
            self.assertEqual( sorted(tp.iterdir()), [fx, fy, fz] )
            assert_symlink(fx, fy, 'x.txt')

            replace_link('x.txt', fy, symbolic=True)  # replace
            self.assertEqual( sorted(tp.iterdir()), [fx, fy, fz] )
            assert_symlink(fx, fy, 'x.txt')

            replace_link(fx, fy, symbolic=True)  # replace with slightly different target
            self.assertEqual( sorted(tp.iterdir()), [fx, fy, fz] )
            assert_symlink(fx, fy, str(fx))

            replace_link(fz, fy, symbolic=True)  # replace with different target
            self.assertEqual( sorted(tp.iterdir()), [fx, fy, fz] )
            assert_symlink(fz, fy, str(fz))

            # force an error on os.replace
            fd = tp/'ddd'
            fd.mkdir()
            with self.assertRaises(IsADirectoryError):
                replace_link(fz, fd, symbolic=True)
            self.assertEqual( sorted(tp.iterdir()), [fd, fx, fy, fz] )
            assert_symlink(fz, fy, str(fz))

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
        if sys.hexversion>=0x030C00B0:  # cover-req-ge3.12  # pragma: no branch
            with NamedTemporaryFile(delete=True, delete_on_close=False) as tf3:  # type: ignore[call-overload, unused-ignore]  # pylint: disable=unexpected-keyword-arg,useless-suppression  # noqa: E501
                tf3.write(b'Quz')
                tf3.close()
                self.assertTrue( Path(tf3.name).exists() )
            self.assertFalse( Path(tf3.name).exists() )

    @unittest.skipIf(condition=sys.platform.startswith('win32'), reason='not on Windows')
    def test_simple_perms(self):  # cover-not-win32
        testcases = (
            # mode, sugg,  dir,   gw,    gw+dir
            (0o444, 0o444, 0o555, 0o444, 0o555),
            (0o555, 0o555, 0o555, 0o555, 0o555),
            (0o644, 0o644, 0o755, 0o664, 0o775),
            (0o755, 0o755, 0o755, 0o775, 0o775),
            (0o000, 0o444, 0o555, 0o444, 0o555),  # 0
            (0o077, 0o444, 0o555, 0o444, 0o555),  # 0
            (0o100, 0o555, 0o555, 0o555, 0o555),  # X
            (0o177, 0o555, 0o555, 0o555, 0o555),  # X
            (0o200, 0o644, 0o755, 0o664, 0o775),  # W
            (0o277, 0o644, 0o755, 0o664, 0o775),  # W
            (0o400, 0o444, 0o555, 0o444, 0o555),  # R
            (0o477, 0o444, 0o555, 0o444, 0o555),  # R
            (0o644|stat.S_ISUID|stat.S_ISGID|stat.S_ISVTX,
             0o644, 0o755, 0o664, 0o775),  # noqa: E127
        )
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            for mode,sugg,dr,gw,gwdr in testcases:
                self.assertEqual( (mode,sugg), simple_perms(mode|stat.S_IFREG) )
                self.assertEqual( (mode,dr),   simple_perms(mode|stat.S_IFDIR) )
                self.assertEqual( (mode,gw),   simple_perms(mode|stat.S_IFREG, group_write=True) )
                self.assertEqual( (mode,gwdr), simple_perms(mode|stat.S_IFDIR, group_write=True) )
            # symlink
            lmode = stat.S_IFLNK|stat.S_IRWXU|stat.S_IRWXG|stat.S_IRWXO
            lperm = stat.S_IMODE(lmode)
            self.assertEqual( (lperm,lperm), simple_perms(lmode) )

    def test_simple_cache(self):
        with (TemporaryDirectory() as tempdir, redirect_stderr(io.StringIO()) as err):
            call_count = 0
            cf = Path(tempdir, '.test.cache')
            @simple_cache(cf)
            def expensive_func():
                nonlocal call_count
                call_count += 1
                return call_count
            self.assertEqual( expensive_func(), 1 )
            self.assertEqual( expensive_func(), 1 )
            self.assertEqual( expensive_func(), 1 )
            cf2 = Path(tempdir, 'test2.cache')
            @simple_cache(cf2, verbose=True)
            def dummy_func():
                nonlocal call_count
                call_count += 1
                return call_count
            self.assertEqual( dummy_func(), 2 )
            self.assertEqual( dummy_func(), 2 )
            self.assertEqual( expensive_func.__wrapped__(), 3 )  # type: ignore[attr-defined]
            self.assertEqual( dummy_func.__wrapped__(), 4 )  # type: ignore[attr-defined]
            self.assertEqual( expensive_func(), 1 )
            self.assertEqual( dummy_func(), 2 )
        self.assertEqual(err.getvalue(), f"Wrote {cf2}\nRead {cf2}\nRead {cf2}\n")

    def test_open_out(self):
        with (TemporaryDirectory() as tempdir, redirect_stdout(io.StringIO()) as out):
            with Pushd(tempdir):
                with open_out(None) as fh:
                    fh.write("Hello")
                with open_out('') as fh:
                    fh.write(", ")
                with open_out('-') as fh:
                    fh.write("World")
                with open_out('hello') as fh:
                    fh.write('world')
                with open('hello', encoding='UTF-8') as fh:
                    self.assertEqual( fh.read(), 'world' )
        self.assertEqual( out.getvalue(), 'Hello, World' )
