"""Error Handling and Formatting Utilities

Overview
--------

This module primarily provides :func:`~igbpyutils.error.javaishstacktrace` and a custom version of
:func:`warnings.showwarning`, both of which produce somewhat shorter messages than the default Python messages.
They can be set up via the context manager :class:`~igbpyutils.error.CustomHandlers` or, more typically, via a
call to :func:`~igbpyutils.error.init_handlers` at the beginning of the script.
This module also provides :func:`~igbpyutils.error.logging_config` for configuration of :mod:`logging`.

Functions
---------

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
import sys
import time
import asyncio
import inspect
import logging
import warnings
import threading
from pathlib import Path
from logging import Formatter
from traceback import extract_tb
from collections.abc import Generator
from typing import Any, Optional, Literal, Union, Protocol, runtime_checkable
import __main__  # just to get __main__.__file__ below
from igbpyutils.file import Filename

def running_in_unittest() -> bool:
    """Attempt to detect if we're running under :mod:`unittest`.

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
    return ex.__name__ if ex.__module__ in ('builtins','__main__') else ex.__module__+"."+ex.__name__

def ex_repr(ex: BaseException) -> str:
    """Return a representation of the exception including its full name and ``.args``."""
    return extype_fullname(type(ex)) + '(' + ', '.join(map(repr, ex.args)) + ')'

# Equivalent to Lib/warnings.py, but customize UserWarning messages to be shorter.
def _showwarning(message, category, filename, lineno, file=None, line=None):  # pylint: disable=too-many-positional-arguments
    if file is None:  # pragma: no branch
        file = sys.stderr
        if file is None:  # pragma: no cover
            return
    if issubclass(category, UserWarning):
        try:
            fn = Path(filename).resolve(strict=True)
        except OSError:  # pragma: no cover
            fn = Path(filename)
        if fn.is_relative_to(_basepath):  # pragma: no branch
            fn = fn.relative_to(_basepath)
        text = f"{extype_fullname(category)}: {message} at {fn}:{lineno}\n"
    else:
        text = warnings.formatwarning(message, category, filename, lineno, line)
    try:
        file.write(text)
    except OSError:  # pragma: no cover
        pass

# NOTE the following four handlers are actually tested, but coverage doesn't see those tests

def _excepthook(_type, value, _traceback):  # pragma: no cover
    for s in javaishstacktrace(value):
        print(s)

def _unraisablehook(unraisable):  # pragma: no cover
    err_msg = unraisable.err_msg if unraisable.err_msg else "Exception ignored in"
    print(f'{err_msg}: {unraisable.object!r}')
    for s in javaishstacktrace(unraisable.exc_value):
        print(s)

def _threading_excepthook(args):  # pragma: no cover
    print(f"In thread {args.thread.name if args.thread else '<unknown>'}:", file=sys.stderr)
    for s in javaishstacktrace(args.exc_value):
        print(s, file=sys.stderr)

def asyncio_exception_handler(loop, ctx :dict[str, Any]):  # pragma: no cover
    """A custom version of :mod:`asyncio`'s ``loop.set_exception_handler()``."""
    print(f"Exception in asyncio: {ctx['message']} ({loop=})", file=sys.stderr)
    for key, val in ctx.items():
        if key not in ('message','exception'):
            print(f"\t{key}: {val!r}", file=sys.stderr)
    if 'exception' in ctx:
        for s in javaishstacktrace(ctx['exception']):
            print(s, file=sys.stderr)

class CustomHandlers:
    """A context manager that installs and removes this module's custom error and warning handlers.

    This modifies :func:`warnings.showwarning`, :func:`sys.excepthook`, :func:`sys.unraisablehook`,
    :func:`threading.excepthook`, and, if there's a running :mod:`asyncio` event loop,
    sets its ``loop.set_exception_handler()`` to :func:`asyncio_exception_handler`. The latter can also
    be done manually later if there is no running loop at the moment."""
    #TODO: Consider providing a way to customize unittest errors: https://github.com/python/cpython/blob/01481f2d/Lib/unittest/result.py#L187
    def __enter__(self):
        self.showwarning_orig = warnings.showwarning  # pylint: disable=attribute-defined-outside-init
        warnings.showwarning = _showwarning
        sys.excepthook = _excepthook
        sys.unraisablehook = _unraisablehook
        # threading.__excepthook__ was not added until 3.10
        self.prev_threading_excepthook = threading.excepthook    # pylint: disable=attribute-defined-outside-init
        threading.excepthook = _threading_excepthook
        self.loop :Optional[asyncio.AbstractEventLoop]  # pylint: disable=attribute-defined-outside-init
        try:
            self.loop = asyncio.get_running_loop()  # pylint: disable=attribute-defined-outside-init
        except RuntimeError:
            self.loop = None  # pylint: disable=attribute-defined-outside-init
        else:  # pragma: no cover
            self.loop.set_exception_handler(asyncio_exception_handler)
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        warnings.showwarning = self.showwarning_orig
        sys.excepthook = sys.__excepthook__
        sys.unraisablehook = sys.__unraisablehook__
        threading.excepthook = self.prev_threading_excepthook
        if self.loop:  # pragma: no cover
            self.loop.set_exception_handler(None)
        return False  # raise exception if any

def init_handlers() -> None:
    """Set up the :class:`CustomHandlers` once and don't change them back."""
    CustomHandlers().__enter__()  # pylint: disable=unnecessary-dunder-call

def javaishstacktrace(ex :BaseException) -> Generator[str, None, None]:
    """Generate a stack trace in the style of Java.

    Compared to Java, the order of exceptions is reversed, so it reads more like a stack.

    Can be used like so: ``"\\n".join(javaishstacktrace(ex))``

    :exc:`AssertionError` is treated specially in that the line of source code that caused them is printed.
    """
    causes = [ex]
    while ex.__cause__:
        ex = ex.__cause__
        causes.append(ex)
    first = True
    for e in reversed(causes):
        r = ex_repr(e)
        if isinstance(e, AssertionError):  # for "assert"s we'd like to see the source that caused it
            # these two should always be true, but guard anyway:
            if e.__traceback__:  # pragma: no branch
                lines = inspect.getinnerframes(e.__traceback__)[-1].code_context
                if lines:  # pragma: no branch
                    r += f" [{ lines[0].strip() if len(lines)==1 else ''.join(lines) !r}]"
        yield r if first else "which caused: " + r
        for item in reversed( extract_tb(e.__traceback__) ):
            try:
                fn = Path(item.filename).resolve(strict=True)
            except OSError:  # pragma: no cover
                fn = Path(item.filename)
            if fn.is_relative_to(_basepath):  # pragma: no branch
                fn = fn.relative_to(_basepath)
            yield f"\tat {fn}:{item.lineno} in {item.name}"
        first = False

class CustomFormatter(Formatter):
    """This is a custom :class:`logging.Formatter` that logs errors using :func:`javaishstacktrace`.

    It also has some better defaults for ``asctime`` formatting (mostly that it is GMT and output with a ``Z`` suffix).

    :seealso: :func:`logging_config`"""
    converter = time.gmtime
    default_time_format = '%Y-%m-%d %H:%M:%S'
    default_msec_format = '%s.%03dZ'
    def formatException(self, ei :tuple) -> str:
        return '\n'.join(javaishstacktrace(ei[1]))

@runtime_checkable
class LoggingStream(Protocol):
    """The minimum required interface of a stream for :class:`logging.StreamHandler`, according to its documentation."""
    def flush(self) -> None: ...    # pragma: no cover
    def write(self, s :str, /) -> int: ...    # pragma: no cover

def logging_config(*,
        level :int = logging.WARNING,
        stream :Union[None, Literal[True], LoggingStream] = None,
        filename :Optional[Filename] = None,
        fmt :Optional[str] = '[%(asctime)s] %(levelname)s %(name)s: %(message)s' ):
    """A replacement for :func:`logging.basicConfig` that uses :class:`CustomFormatter` and has a few more useful defaults.

    :param level: Set the root logger level to the specified level. Defaults to :data:`logging.WARNING`.
    :param stream: Use the specified stream to initialize the :class:`~logging.StreamHandler`.
        Can also be :obj:`True` to specify that :data:`sys.stderr` should be used (which is the default anyway,
        except when a filename is specified).
    :param filename: Specifies that a :class:`~logging.FileHandler` be created using the specified filename.
    :param fmt: Use the specified format string for the handler(s).

    Other defaults are: Files are always encoded with UTF-8, and any existing handlers are always removed.

    Note I also recommend using :func:`logging.captureWarnings`."""
    #TODO: Actually, logging.captureWarnings doesn't make a very good-looking logging message; we might want to write our own version...
    #TODO Later: Consider adding a function that only checks and/or modifies the formatters of existing handlers
    if stream is None and filename is None or stream is True:
        stream = sys.stderr
    if stream is not None and not isinstance(stream, LoggingStream):
        raise TypeError(f"not a LoggingStream: {type(stream)}")
    root = logging.getLogger()
    for hnd in root.handlers[:]:  # attribute is not documented, but this is what logging.basicConfig does
        root.removeHandler(hnd)
        hnd.close()
    handlers :list[logging.Handler] = []
    if stream is not None:
        handlers.append(logging.StreamHandler(stream))
    if filename is not None:
        handlers.append(logging.FileHandler(filename, encoding='UTF-8', errors='namereplace'))
    assert handlers
    fmtr = CustomFormatter(fmt=fmt)
    for hnd in handlers:
        hnd.setFormatter(fmtr)
        root.addHandler(hnd)
    root.setLevel(level)
