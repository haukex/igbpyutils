#!/usr/bin/env python3
"""Tests for ``igbpyutils.error``.

Author, Copyright, and License
------------------------------
Copyright (c) 2022 Hauke Daempfling (haukex@zero-g.net)
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
import io
import sys
import os
import subprocess
import inspect
from contextlib import redirect_stderr
from pathlib import Path
from warnings import warn
from igbpyutils.error import running_in_unittest, javaishstacktrace, CustomHandlers, init_handlers, extype_fullname, ex_repr
# noinspection PyProtectedMember
from igbpyutils.error import _basepath
import tests.error_test_funcs
import tests.error_test_unraisable

class TestErrorUtils(unittest.TestCase):

    def setUp(self):
        self.mybasepath = Path(__file__).parent.parent.joinpath('tests').resolve(strict=True).relative_to(_basepath)
        self.maxDiff = None
        # for subprocess.run: env must include SYSTEMROOT, so just make a copy of the current env and add to it
        self.environ = dict(os.environ)
        self.environ['PYTHONPATH'] = str(Path(__file__).parent.parent)

    def test_error_names(self):
        from tests.error_test_funcs import TestError
        self.assertEqual( extype_fullname(TestError), 'tests.error_test_funcs.TestError' )
        self.assertEqual( extype_fullname(TimeoutError), 'TimeoutError' )
        self.assertEqual( ex_repr( TestError('Hello', 'world') ), "tests.error_test_funcs.TestError('Hello', 'world')" )
        self.assertEqual( ex_repr( ConnectionResetError('foo', 'bar') ), "ConnectionResetError('foo', 'bar')" )

    def test_running_in_unittest(self):
        self.assertTrue(running_in_unittest())
        sp1 = subprocess.run([sys.executable, '-c', 'import igbpyutils.error; print(repr(igbpyutils.error.running_in_unittest()))'],
            check=True, capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ)
        self.assertEqual(b'False', sp1.stdout.strip())
        self.assertEqual(b'', sp1.stderr)
        sp2 = subprocess.run([sys.executable, '-c', 'import unittest; import igbpyutils.error; print(repr(igbpyutils.error.running_in_unittest()))'],
            check=True, capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ)
        self.assertEqual(b'False', sp2.stdout.strip())
        self.assertEqual(b'', sp2.stderr)

    def test_excepthook(self):
        sp = subprocess.run([sys.executable, tests.error_test_funcs.__file__],
            capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ )
        self.assertNotEqual(0, sp.returncode)
        self.assertEqual(b'', sp.stderr)
        self.assertEqual(
            "TestError('test error 1')\n"
            f"\tat error_test_funcs.py:23 in testfunc3\n"
            f"\tat error_test_funcs.py:18 in testfunc2\n"
            "which caused: ValueError('test error 2')\n"
            f"\tat error_test_funcs.py:20 in testfunc2\n"
            f"\tat error_test_funcs.py:12 in testfunc1\n"
            "which caused: TypeError('test error 3')\n"
            f"\tat error_test_funcs.py:14 in testfunc1\n"
            f"\tat error_test_funcs.py:8 in testfunc0\n"
            f"\tat error_test_funcs.py:29 in <module>\n",
            sp.stdout.decode("ASCII").replace("\r\n","\n") )

    def test_unraisablehook(self):
        sp = subprocess.run([sys.executable, tests.error_test_unraisable.__file__],
            capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ )
        self.assertEqual(0, sp.returncode)
        self.assertEqual(b'', sp.stderr)
        self.assertRegex(sp.stdout.decode("ASCII"),
            r'''\AException ignored in: <function Foo\.__del__ at 0x[0-9A-Fa-f]+>\r?\n'''
            r'''RuntimeError\('Bar'\)\r?\n'''
            r'''\tat error_test_unraisable.py:6 in testfunc\r?\n'''
            r'''\tat error_test_unraisable.py:10 in __del__\r?\n\Z''')

    def test_javaishstacktrace(self):
        exline = None
        try:
            exline = inspect.stack()[0].lineno + 1
            tests.error_test_funcs.testfunc0()
        except TypeError as ex:
            self.assertEqual(
                ("tests.error_test_funcs.TestError('test error 1')",
                f"\tat {self.mybasepath/'error_test_funcs.py'}:23 in testfunc3",
                f"\tat {self.mybasepath/'error_test_funcs.py'}:18 in testfunc2",
                "which caused: ValueError('test error 2')",
                f"\tat {self.mybasepath/'error_test_funcs.py'}:20 in testfunc2",
                f"\tat {self.mybasepath/'error_test_funcs.py'}:12 in testfunc1",
                "which caused: TypeError('test error 3')",
                f"\tat {self.mybasepath/'error_test_funcs.py'}:14 in testfunc1",
                f"\tat {self.mybasepath/'error_test_funcs.py'}:8 in testfunc0",
                f"\tat {self.mybasepath/'test_error.py'}:{exline} in test_javaishstacktrace"),
                tuple(javaishstacktrace(ex)) )
        # check our extension to AssertionErrors
        self.assertTrue(__debug__)
        try:
            exline = inspect.stack()[0].lineno + 1
            assert 1+1==3
        except AssertionError as ex:
            self.assertEqual(
                ("AssertionError() ['assert 1+1==3']",
                 f"\tat {self.mybasepath/'test_error.py'}:{exline} in test_javaishstacktrace"),
                tuple(javaishstacktrace(ex)) )

    def test_customwarn(self):
        with redirect_stderr(io.StringIO()) as s:
            warnline = inspect.stack()[0].lineno
            warn("Test 1")
            with CustomHandlers(): warn("Test 2"); \
                warn("Test 3", RuntimeWarning)
            warn("Test 4")
            init_handlers(); warn("Test 5")
        self.assertEqual(
            f'{__file__}:{warnline+1}: UserWarning: Test 1\n  warn("Test 1")\n'
            f'UserWarning: Test 2 at {self.mybasepath/"test_error.py"}:{warnline+2}\n'
            f'{__file__}:{warnline+3}: RuntimeWarning: Test 3\n  warn("Test 3", RuntimeWarning)\n'
            f'{__file__}:{warnline+4}: UserWarning: Test 4\n  warn("Test 4")\n'
            f'UserWarning: Test 5 at {self.mybasepath/"test_error.py"}:{warnline+5}\n', s.getvalue())

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
