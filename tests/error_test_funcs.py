#!/usr/bin/env python

# WARNING: Line numbers in this file are hard-coded in test_error.py!

class TestError(RuntimeError): pass

def testfunc0():
    testfunc1()

def testfunc1():
    try:
        testfunc2()
    except ValueError as ex:
        raise TypeError("test error 3") from ex

def testfunc2():
    try:
        testfunc3()
    except RuntimeError as ex:
        raise ValueError("test error 2") from ex

def testfunc3():
    raise TestError("test error 1")

# for testing of sys.excepthook
if __name__ == '__main__':  # pragma: no cover
    import igbpyutils.error
    igbpyutils.error.init_handlers()
    testfunc0()
