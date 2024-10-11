"""Tests for ``igbpyutils.error``.

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
import logging
import inspect
import unittest
import subprocess
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from warnings import warn, simplefilter, catch_warnings
from igbpyutils.file import NamedTempFileDeleteLater
from igbpyutils.error import (running_in_unittest, javaishstacktrace, CustomHandlers, init_handlers, extype_fullname,
                              ex_repr, CustomFormatter, logging_config)
from igbpyutils.error import _basepath  # pyright: ignore [reportPrivateUsage]
from tests.error_test_funcs import TestError
import tests.error_test_funcs
import tests.error_test_unraisable
import tests.error_test_thread
import tests.error_test_async

class TestErrorUtils(unittest.TestCase):

    def setUp(self):
        self.mybasepath = Path(__file__).parent.parent.joinpath('tests').resolve(strict=True).relative_to(_basepath)
        self.maxDiff = None  # pylint: disable=invalid-name
        # for subprocess.run: env must include SYSTEMROOT, so just make a copy of the current env and add to it
        self.environ = dict(os.environ)
        self.environ['PYTHONPATH'] = str(Path(__file__).parent.parent)

    def test_error_names(self):
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
            capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ, check=False )
        self.assertNotEqual(0, sp.returncode)
        self.assertEqual(b'', sp.stderr)
        self.assertEqual(
            "TestError('test error 1')\n"
            "\tat error_test_funcs.py:23 in testfunc3\n"
            "\tat error_test_funcs.py:18 in testfunc2\n"
            "which caused: ValueError('test error 2')\n"
            "\tat error_test_funcs.py:20 in testfunc2\n"
            "\tat error_test_funcs.py:12 in testfunc1\n"
            "which caused: TypeError('test error 3')\n"
            "\tat error_test_funcs.py:14 in testfunc1\n"
            "\tat error_test_funcs.py:8 in testfunc0\n"
            "\tat error_test_funcs.py:29 in <module>\n",
            sp.stdout.decode("ASCII").replace("\r\n","\n") )

    def test_unraisablehook(self):
        sp = subprocess.run([sys.executable, tests.error_test_unraisable.__file__],
            capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ, check=False )
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
        with redirect_stderr(io.StringIO()) as s, catch_warnings():
            simplefilter('default')
            warnline = inspect.stack()[0].lineno
            warn("Test 1")
            with CustomHandlers(): warn("Test 2"  # pylint: disable=multiple-statements  # noqa: E701
                                        ); warn("Test 3", RuntimeWarning)  # noqa: E702
            warn("Test 4")
            init_handlers(); warn("Test 5")  # pylint: disable=multiple-statements  # noqa: E702
        self.assertEqual(
            f'{__file__}:{warnline+1}: UserWarning: Test 1\n  warn("Test 1")\n'
            f'UserWarning: Test 2 at {self.mybasepath/"test_error.py"}:{warnline+2}\n'
            f'{__file__}:{warnline+3}: RuntimeWarning: Test 3\n  ); warn("Test 3", RuntimeWarning)  # noqa: E702\n'
            f'{__file__}:{warnline+4}: UserWarning: Test 4\n  warn("Test 4")\n'
            f'UserWarning: Test 5 at {self.mybasepath/"test_error.py"}:{warnline+5}\n', s.getvalue())

    def test_threadexcept(self):
        with self.assertRaises(RuntimeError):
            tests.error_test_thread.testfunc0()
        sp = subprocess.run([sys.executable, tests.error_test_thread.__file__],
            capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ, check=False )
        self.assertEqual(0, sp.returncode)
        self.assertEqual(b'', sp.stdout)
        self.assertRegex(sp.stderr.decode("ASCII"),
            r'''\AIn thread .+:\r?\n'''
            r'''RuntimeError\('Foo'\)\r?\n'''
            r'''\tat error_test_thread.py:10 in testfunc1\r?\n'''
            r'''\tat error_test_thread.py:7 in testfunc0\r?\n'''
            r'''(?:\tat .+threading\.py.+\r?\n)+\Z''')

    def test_asyncioexcept(self):
        sp = subprocess.run([sys.executable, tests.error_test_async.__file__],
            capture_output=True, cwd=Path(__file__).parent.parent, env=self.environ, check=False )
        self.assertEqual(0, sp.returncode)
        self.assertEqual(b'', sp.stdout)
        self.assertRegex(sp.stderr.decode("ASCII"),
            r'''\AException in asyncio: Task exception was never retrieved \(loop=.+\)\r?\n'''
            r'''\s+future: .+\r?\n'''
            r'''(?:\s+source_traceback: .+\r?\n)?'''
            r'''RuntimeError\('Quz'\)\r?\n'''
            r'''\s+at error_test_async.py:11 in testfunc1\r?\n'''
            r'''\s+at error_test_async.py:8 in testfunc0\r?\n\Z''')

    def test_formatter(self):
        msgs = io.StringIO()
        logger = logging.getLogger("test_formatter")
        logger.propagate = False
        handler = logging.StreamHandler(msgs)
        handler.setFormatter(CustomFormatter('%(levelname)s %(name)s: %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        exline = None
        try:
            exline = inspect.stack()[0].lineno + 1
            raise RuntimeError("Boom")
        except RuntimeError as ex:
            logger.error("Exception", exc_info=ex)
        self.assertEqual( msgs.getvalue(), "ERROR test_formatter: Exception\n"
            f"RuntimeError('Boom')\n\tat {self.mybasepath/'test_error.py'}:{exline} in test_formatter\n" )

    def test_logging_config(self):
        # Note I used to patch time.time here, but that no longer works as of Python 3.13, so just drop the time
        with self.assertRaises(TypeError):
            logging_config(stream="")  # type: ignore[arg-type]
        logger = logging.getLogger("test_logging_config")
        with (redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err):
            logging_config(fmt='%(levelname)s %(name)s: %(message)s')
            logger.warning("Hello, World!")
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), 'WARNING test_logging_config: Hello, World!\n')
        out = io.StringIO()
        logging_config(stream=out, fmt='%(levelname)s %(name)s: %(message)s')
        logger.error("Bang")
        self.assertEqual(out.getvalue(), 'ERROR test_logging_config: Bang\n')
        with NamedTempFileDeleteLater() as ntf:
            ntf.close()
            with (redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err):
                logging_config(filename=ntf.name, fmt='%(levelname)s %(name)s: %(message)s')
                logger.critical("BOOM")
                logging_config(filename=ntf.name, stream=True, level=logging.INFO,
                               fmt='%(levelname)s in %(name)s: %(message)s')
                logger.debug("Test")
                logger.info("What's up?")
                logging_config(fmt='%(levelname)s %(name)s: %(message)s')
                logger.info("Nope")
                logger.warning("Hi there")
            for hnd in logging.getLogger().handlers:
                hnd.close()  # so the file gets closed, needed on Windows to read the file
            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(),
                             "INFO in test_logging_config: What's up?\n"
                             "WARNING test_logging_config: Hi there\n")
            with open(ntf.name, encoding='UTF-8') as fh:
                self.assertEqual(fh.read(),
                                 'CRITICAL test_logging_config: BOOM\n'
                                 "INFO in test_logging_config: What's up?\n")
