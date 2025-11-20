#!/usr/bin/env python

# WARNING: Line numbers in this file are hard-coded in test_error.py!
# spell-checker: ignore testfunc excepthook

def testfunc():  # pragma: no cover
    raise RuntimeError("Bar")

class Foo:
    def __del__(self):  # pragma: no cover
        testfunc()

if __name__ == '__main__':  # pragma: no cover
    import igbpyutils.error
    import gc
    from typing import Optional
    # only set up our custom handlers when we're run, not loaded as a module!
    igbpyutils.error.init_handlers()
    foo :Optional[Foo] = Foo()
    foo = None  # pylint: disable=disallowed-name
    gc.collect()
