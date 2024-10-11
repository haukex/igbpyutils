"""Tests for ``igbpyutils.dev``.

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
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from contextlib import redirect_stdout
from io import TextIOWrapper, StringIO
from tempfile import TemporaryDirectory
from igbpyutils.file import NamedTempFileDeleteLater
from igbpyutils.dev.script_vs_lib import ScriptLibFlags, ScriptLibResult, ResultLevel, check_script_vs_lib
import igbpyutils.dev.script_vs_lib as uut

def write_test_file(name, bfh, flags :ScriptLibFlags, *, shebang :str = "#!/usr/bin/env python"):
    with TextIOWrapper(bfh, encoding='UTF-8') as fh:
        if flags&ScriptLibFlags.SHEBANG:
            fh.write(shebang+"\n")
        fh.write("import sys\n")  # Import
        fh.write("import json as JSON\n")
        fh.write("from functools import partial\n")  # ImportFrom
        fh.write("def foo(): pass\n")  # FunctionDef
        fh.write("async def bar(): pass\n")  # AsyncFunctionDef
        fh.write("class FooBar: pass\n")  # ClassDef
        fh.write("CONSTANT = 'Hello'\n")  # Assign
        fh.write("X :int = 42\n")  # AnnAssign
        fh.write("assert True\n")  # Assert
        if flags&ScriptLibFlags.SCRIPT_LIKE:
            fh.write("print('Hello')\n")
        if flags&ScriptLibFlags.NAME_MAIN:
            fh.write("if __name__=='__main__': pass\n")
    bfh.close()
    os.chmod(name, 0o755 if flags&ScriptLibFlags.EXEC_BIT else 0o644)  # should be ignored on Windows

_ = """
In the following:
- "755" and "exec" mean whether the exec bit is set (variable ``exec_is_set``)
- "#!/" and "shebang" mean whether the shebang line is present (variable ``shebang``)
- "if" means whether there is a ``if __name__ == "__main__"`` present (variable ``has_name_eq_main``)
- "scr" and "script" mean that the file contains statements that make it look like a script
  (such as `print`, `for`, etc.) (variable ``looks_like_script``)
- "Covered" is a development note for myself as to whether I've covered this condition.

+=====+=====+=====+=====+=================================+
| 755 | #!/ | if  | scr | Then                            |
+=====+=====+=====+=====+=================================+
|  0  |  0  |  0  |  0  | Normal library                  |
+-----+-----+-----+-----+---------------------------------+
|  0  |  0  |  0  |  1  | Missing shebang and exec        |
+-----+-----+-----+-----+---------------------------------+
|  0  |  0  |  1  |  0  | Missing shebang and exec        |
+-----+-----+-----+-----+---------------------------------+
|  0  |  0  |  1  |  1  | Bad: both "if" and script       |
+-----+-----+-----+-----+---------------------------------+
|  0  |  1  |  0  |  0  | Missing "if"/script (and exec)  |
+-----+-----+-----+-----+---------------------------------+
|  0  |  1  |  0  |  1  | Missing exec                    |
+-----+-----+-----+-----+---------------------------------+
|  0  |  1  |  1  |  0  | Missing exec                    |
+-----+-----+-----+-----+---------------------------------+
|  0  |  1  |  1  |  1  | Bad: both "if" and script       |
+-----+-----+-----+-----+---------------------------------+
|  1  |  0  |  0  |  0  | Bad: Library has exec set       |
+-----+-----+-----+-----+---------------------------------+
|  1  |  0  |  0  |  1  | Missing shebang                 |
+-----+-----+-----+-----+---------------------------------+
|  1  |  0  |  1  |  0  | Missing shebang                 |
+-----+-----+-----+-----+---------------------------------+
|  1  |  0  |  1  |  1  | Bad: both "if" and script       |
+-----+-----+-----+-----+---------------------------------+
|  1  |  1  |  0  |  0  | Missing "if"/script             |
+-----+-----+-----+-----+---------------------------------+
|  1  |  1  |  0  |  1  | Normal script (could use "if")  |
+-----+-----+-----+-----+---------------------------------+
|  1  |  1  |  1  |  0  | Normal script (could use "if")  |
+-----+-----+-----+-----+---------------------------------+
|  1  |  1  |  1  |  1  | Bad: both "if" and script       |
+-----+-----+-----+-----+---------------------------------+
"""
test_cases = (
    ScriptLibResult(Path(), ResultLevel.INFO, "File looks like a normal library",
                    ScriptLibFlags(0)),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to Expr@L10) but is missing exec bit and shebang",
                    ScriptLibFlags.SCRIPT_LIKE),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to `if __name__=='__main__'`) but is missing exec bit and shebang",
                    ScriptLibFlags.NAME_MAIN),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File has `if __name__=='__main__'` and looks like a script due to Expr@L10",
                    ScriptLibFlags.SCRIPT_LIKE|ScriptLibFlags.NAME_MAIN),

    ScriptLibResult(Path(), ResultLevel.ERROR, "File has shebang but seems to be missing anything script-like",
                    ScriptLibFlags.SHEBANG),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to Expr@L11) but is missing exec bit",
                    ScriptLibFlags.SHEBANG|ScriptLibFlags.SCRIPT_LIKE),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to `if __name__=='__main__'`) but is missing exec bit",
                    ScriptLibFlags.SHEBANG|ScriptLibFlags.NAME_MAIN),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File has `if __name__=='__main__'` and looks like a script due to Expr@L11",
                    ScriptLibFlags.SHEBANG|ScriptLibFlags.SCRIPT_LIKE|ScriptLibFlags.NAME_MAIN),  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501

    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a library but exec bit is set",
                    ScriptLibFlags.EXEC_BIT),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to Expr@L10) but is missing shebang",
                    ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SCRIPT_LIKE),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to `if __name__=='__main__'`) but is missing shebang",
                    ScriptLibFlags.EXEC_BIT|ScriptLibFlags.NAME_MAIN),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File has `if __name__=='__main__'` and looks like a script due to Expr@L10",
                    ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SCRIPT_LIKE|ScriptLibFlags.NAME_MAIN),  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501

    ScriptLibResult(Path(), ResultLevel.ERROR, "File has shebang and exec bit but seems to be missing anything script-like",
                    ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SHEBANG),
    ScriptLibResult(Path(), ResultLevel.NOTICE, "File looks like a normal script (but could use `if __name__=='__main__'`)",
                    ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SHEBANG|ScriptLibFlags.SCRIPT_LIKE),  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501
    ScriptLibResult(Path(), ResultLevel.INFO, "File looks like a normal script",
                    ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SHEBANG|ScriptLibFlags.NAME_MAIN),  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501
    ScriptLibResult(Path(), ResultLevel.ERROR, "File has `if __name__=='__main__'` and looks like a script due to Expr@L11",
                    ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SHEBANG|ScriptLibFlags.SCRIPT_LIKE  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501
                    |ScriptLibFlags.NAME_MAIN),
)

IS_WINDOWS = sys.platform.startswith('win32')

_ = """
Windows:

+=====+=====+=====+=================================+
| #!/ | if  | scr | Then                            |
+=====+=====+=====+=================================+
|  0  |  0  |  0  | Normal library                  |
+-----+-----+-----+---------------------------------+
|  0  |  0  |  1  | Missing shebang                 |
+-----+-----+-----+---------------------------------+
|  0  |  1  |  0  | Missing shebang                 |
+-----+-----+-----+---------------------------------+
|  0  |  1  |  1  | Bad: both "if" and script       |
+-----+-----+-----+---------------------------------+
|  1  |  0  |  0  | Missing "if"/script             |
+-----+-----+-----+---------------------------------+
|  1  |  0  |  1  | Normal script (could use "if")  |
+-----+-----+-----+---------------------------------+
|  1  |  1  |  0  | Normal script                   |
+-----+-----+-----+---------------------------------+
|  1  |  1  |  1  | Bad: both "if" and script       |
+-----+-----+-----+---------------------------------+

Possible To-Do for Later: Would be cool if the function *automatically* detected a git repo and check its perms...
"""
win_test_cases = (
    ScriptLibResult(Path(), ResultLevel.INFO, "File looks like a normal library",
                    ScriptLibFlags(0)),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to Expr@L10) but is missing shebang",
                    ScriptLibFlags.SCRIPT_LIKE),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File looks like a script (due to `if __name__=='__main__'`) but is missing shebang",
                    ScriptLibFlags.NAME_MAIN),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File has `if __name__=='__main__'` and looks like a script due to Expr@L10",
                    ScriptLibFlags.SCRIPT_LIKE|ScriptLibFlags.NAME_MAIN),

    ScriptLibResult(Path(), ResultLevel.ERROR, "File has shebang but seems to be missing anything script-like",
                    ScriptLibFlags.SHEBANG),
    ScriptLibResult(Path(), ResultLevel.NOTICE, "File looks like a normal script (but could use `if __name__=='__main__'`)",
                    ScriptLibFlags.SHEBANG|ScriptLibFlags.SCRIPT_LIKE),
    ScriptLibResult(Path(), ResultLevel.INFO, "File looks like a normal script",
                    ScriptLibFlags.SHEBANG|ScriptLibFlags.NAME_MAIN),
    ScriptLibResult(Path(), ResultLevel.ERROR, "File has `if __name__=='__main__'` and looks like a script due to Expr@L11",
                    ScriptLibFlags.SHEBANG|ScriptLibFlags.SCRIPT_LIKE|ScriptLibFlags.NAME_MAIN),  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501
)

class TestScriptVsLib(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_script_vs_lib(self):
        for case in win_test_cases if IS_WINDOWS else test_cases:
            with NamedTempFileDeleteLater(suffix='.py') as ntf:
                path = Path(ntf.name)
                write_test_file(path, ntf, case.flags)
                self.assertEqual( check_script_vs_lib(path), case._replace(path=path) )
        case1 = ScriptLibResult(Path(), ResultLevel.WARNING, "File has unrecognized shebang '#!/bin/python'",
                                ScriptLibFlags.SHEBANG)
        with NamedTempFileDeleteLater(suffix='.py') as ntf:
            path = Path(ntf.name)
            write_test_file(path, ntf, case1.flags, shebang='#!/bin/python')
            self.assertEqual( check_script_vs_lib(path, known_shebangs=('#!/usr/bin/python',)), case1._replace(path=path) )

    def test_script_vs_lib_git(self):
        with TemporaryDirectory() as td:
            tdr = Path(td)
            subprocess.run(['git','init','--quiet'], cwd=td, check=True)
            subprocess.run(['git','config','--local','user.email','git@example.com'], cwd=td, check=True)
            subprocess.run(['git','config','--local','user.name','CI Test'], cwd=td, check=True)
            subprocess.run(['git','config','--local','core.autocrlf','false'], cwd=td, check=True)
            subprocess.run(['git','config','--local','core.fileMode','false'], cwd=td, check=True)
            (tdr/'lib').mkdir()
            pyl = tdr/'lib'/'library.py'
            with pyl.open('wb') as fh:
                write_test_file(pyl, fh, ScriptLibFlags(0))
            pys = tdr/'script.py'
            with pys.open('wb') as fh:
                write_test_file(pys, fh, ScriptLibFlags.SHEBANG|ScriptLibFlags.NAME_MAIN)
            subprocess.run(['git','add',pyl.relative_to(td),pys.relative_to(td)], cwd=td, check=True)
            self.assertEqual(check_script_vs_lib(pyl, exec_from_git=True),
                             ScriptLibResult( pyl, ResultLevel.INFO,"File looks like a normal library", ScriptLibFlags(0) ))
            self.assertEqual(check_script_vs_lib(pys, exec_from_git=True),
                             ScriptLibResult( pys, ResultLevel.ERROR, "File looks like a script (due to `if __name__=='__main__'`) "
                                             "but is missing exec bit", ScriptLibFlags.SHEBANG|ScriptLibFlags.NAME_MAIN ))
            subprocess.run(['git','update-index','--chmod=+x',pyl.relative_to(td),pys.relative_to(td)], cwd=td, check=True)
            self.assertEqual(check_script_vs_lib(pyl, exec_from_git=True),
                             ScriptLibResult( pyl, ResultLevel.ERROR, "File looks like a library but exec bit is set", ScriptLibFlags.EXEC_BIT))
            self.assertEqual(check_script_vs_lib(pys, exec_from_git=True),
                             ScriptLibResult( pys, ResultLevel.INFO, "File looks like a normal script",
                                             ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SHEBANG|ScriptLibFlags.NAME_MAIN ))  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501
            subprocess.run(['git','commit','--quiet','--message','test2'], cwd=td, check=True)
            self.assertEqual(check_script_vs_lib(pyl, exec_from_git=True),
                             ScriptLibResult( pyl, ResultLevel.ERROR, "File looks like a library but exec bit is set", ScriptLibFlags.EXEC_BIT))
            self.assertEqual(check_script_vs_lib(pys, exec_from_git=True),
                             ScriptLibResult( pys, ResultLevel.INFO, "File looks like a normal script",
                                             ScriptLibFlags.EXEC_BIT|ScriptLibFlags.SHEBANG|ScriptLibFlags.NAME_MAIN ))  # pylint: disable=unsupported-binary-operation,useless-suppression  # noqa: E501
            with (self.assertRaises(RuntimeError),
                  patch('subprocess.run', return_value=SimpleNamespace(returncode=0, stderr='', stdout='something'))):
                check_script_vs_lib(pys, exec_from_git=True)
            with (self.assertRaises(RuntimeError),
                  patch('subprocess.run', return_value=SimpleNamespace(returncode=0, stderr='',
                  stdout='100644 2fdef5822492003bcf91a1ea8e73cd7b6ea01ba2 0\tnot-script.py\n'))):
                check_script_vs_lib(pys, exec_from_git=True)

    def test_script_vs_lib_cli(self):
        with TemporaryDirectory() as td:
            tdr = Path(td)
            (tdr/'dummy.txt').touch()
            py1 = tdr/'one.py'
            with py1.open('wb') as fh:
                write_test_file(py1, fh, ScriptLibFlags(0))  # library
            py2 = tdr/'two.py'
            with py2.open('wb') as fh:
                write_test_file(py2, fh, ScriptLibFlags.SHEBANG)  # bad
            py3 = tdr/'three.py'
            with py3.open('wb') as fh:
                write_test_file(py3, fh, ScriptLibFlags.SHEBANG  # pylint: disable=unsupported-binary-operation,useless-suppression
                                |ScriptLibFlags.SCRIPT_LIKE|ScriptLibFlags.EXEC_BIT)  # notice

            out1 = StringIO()
            sys.argv = ["py-check-script-vs-lib", str(tdr)]
            with (redirect_stdout(out1), patch('argparse.ArgumentParser.exit') as mock1):
                uut.main()
            mock1.assert_called_once_with(1)
            self.assertEqual( out1.getvalue(), f"ERROR {py2}: File has shebang but seems to be missing anything script-like\n")

            out2 = StringIO()
            sys.argv = ["py-check-script-vs-lib", "-n", str(tdr)]
            with (redirect_stdout(out2), patch('argparse.ArgumentParser.exit') as mock2):
                uut.main()
            mock2.assert_called_once_with(2)
            self.assertEqual( sorted(out2.getvalue().splitlines()), [
                f"ERROR {py2}: File has shebang but seems to be missing anything script-like",
                f"NOTICE {py3}: File looks like a normal script (but could use `if __name__=='__main__'`)",
            ])

            out3 = StringIO()
            sys.argv = ["py-check-script-vs-lib", "-v", str(tdr)]
            with (redirect_stdout(out3), patch('argparse.ArgumentParser.exit') as mock3):
                uut.main()
            mock3.assert_called_once_with(1)
            self.assertEqual( sorted(out3.getvalue().splitlines()), [
                f"ERROR {py2}: File has shebang but seems to be missing anything script-like",
                f"INFO {py1}: File looks like a normal library",
                f"NOTICE {py3}: File looks like a normal script (but could use `if __name__=='__main__'`)",
            ])
