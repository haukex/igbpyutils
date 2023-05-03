#!python3
"""Library with error handling and formatting utilities.

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
import sys
import inspect
import warnings
from collections.abc import Generator
from pathlib import Path
# noinspection PyPackageRequirements
import __main__  # just to get __main__.__file__ below
from traceback import extract_tb

def running_in_unittest() -> bool:
    """Attempt to detect if we're running under ``unittest``.

    This is slightly hackish and used in this module only for slightly nicer output during testing."""
    # note the following is actually tested, but the "false" case isn't seen by the "coverage" tool
    return 'unittest' in sys.modules and any(  # pragma: no cover
        Path(stack_frame.frame.f_code.co_filename).parts[-2:] == ('unittest','main.py')
        for stack_frame in inspect.stack() )

_basepath = Path(__main__.__file__).parent.resolve(strict=True) \
    if hasattr(__main__, '__file__') and not running_in_unittest() \
    else Path().resolve(strict=True)  # just the CWD

def extype_fullname(ex: type) -> str:
    """Return the name of an exception together with its module name, if any."""
    if ex.__module__ in ('builtins','__main__'): return ex.__name__
    else: return ex.__module__ + "." + ex.__name__

def ex_repr(ex: BaseException) -> str:
    """Return a representation of the exception including its full name and ``.args``."""
    return extype_fullname(type(ex)) + '(' + ', '.join(map(repr, ex.args)) + ')'

# Equivalent to Lib/warnings.py, but customize UserWarning messages to be shorter.
def _showwarning(message, category, filename, lineno, file=None, line=None):
    if file is None:  # pragma: no cover
        file = sys.stderr
        if file is None: return
    if issubclass(category, UserWarning):
        try:
            fn = Path(filename).resolve(strict=True)
        except OSError:  # pragma: no cover
            fn = Path(filename)
        if fn.is_relative_to(_basepath): fn = fn.relative_to(_basepath)
        text = f"{extype_fullname(category)}: {message} at {fn}:{lineno}\n"
    else:
        text = warnings.formatwarning(message, category, filename, lineno, line)
    try: file.write(text)
    except OSError: pass  # pragma: no cover

def _excepthook(_type, value, _traceback):  # pragma: no cover
    for s in javaishstacktrace(value): print(s)

def _unraisablehook(unraisable):  # pragma: no cover
    err_msg = unraisable.err_msg if unraisable.err_msg else "Exception ignored in"
    print(f'{err_msg}: {unraisable.object!r}')
    for s in javaishstacktrace(unraisable.exc_value): print(s)

class CustomHandlers:
    """A context manager that installs and removes this module's custom error and warning handlers.

    This modifies ``warnings.showwarning``, ``sys.excepthook``, and ``sys.unraisablehook``."""
    def __enter__(self):
        self.showwarning_orig = warnings.showwarning
        warnings.showwarning = _showwarning
        sys.excepthook = _excepthook
        sys.unraisablehook = _unraisablehook
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        warnings.showwarning = self.showwarning_orig
        sys.excepthook = sys.__excepthook__
        sys.unraisablehook = sys.__unraisablehook__
        return False  # raise exception if any

def init_handlers() -> None:
    """Set up the ``CustomHandlers`` once and don't change them back."""
    CustomHandlers().__enter__()

def javaishstacktrace(ex :BaseException) -> Generator[str, None, None]:
    """Generate a stack trace in the style of Java.

    Compared to Java, the order of exceptions is reversed, so it reads more like a stack.

    ``AssertionError``s are treated specially in that the line of source code that caused them is printed.
    """
    causes = [ex]
    while ex.__cause__:
        ex = ex.__cause__
        causes.append(ex)
    first = True
    for e in reversed(causes):
        r = ex_repr(e)
        if isinstance(e, AssertionError):  # for "assert"s we'd like to see the source that caused it
            assert e.__traceback__  # for some reason, the coverage tool is reporting the following `if` is false on 3.9?
            if e.__traceback__:  # cover-not-le3.9
                lines = inspect.getinnerframes(e.__traceback__)[-1].code_context
                if lines:
                    r += f" [{ lines[0].strip() if len(lines)==1 else ''.join(lines) !r}]"
                else: pass  # pragma: no cover
            else: pass  # cover-not-ge3.10
        yield r if first else "which caused: " + r
        for item in reversed( extract_tb(e.__traceback__) ):
            try:
                fn = Path(item.filename).resolve(strict=True)
            except OSError:  # pragma: no cover
                fn = Path(item.filename)
            if fn.is_relative_to(_basepath): fn = fn.relative_to(_basepath)
            yield f"\tat {fn}:{item.lineno} in {item.name}"
        first = False
