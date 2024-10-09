#!/usr/bin/env python
from threading import Thread

# WARNING: Line numbers in this file are hard-coded in test_error.py!

def testfunc0():
    testfunc1()

def testfunc1():
    raise RuntimeError("Foo")

# for testing of sys.excepthook
if __name__ == '__main__':  # pragma: no cover
    import igbpyutils.error
    igbpyutils.error.init_handlers()
    thr = Thread(target=testfunc0)
    thr.start()
    thr.join(5)
