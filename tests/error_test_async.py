#!/usr/bin/env python
import asyncio
import igbpyutils.error

# WARNING: Line numbers in this file are hard-coded in test_error.py!
# spell-checker: ignore testfunc excepthook

async def testfunc0():  # pragma: no cover
    await testfunc1()

async def testfunc1():  # pragma: no cover
    raise RuntimeError("Quz")

async def main():  # pragma: no cover
    #asyncio.get_running_loop().set_exception_handler(lambda _loop,data: print(repr(data)))
    igbpyutils.error.init_handlers()
    asyncio.create_task(testfunc0())

# for testing of sys.excepthook
if __name__ == '__main__':  # pragma: no cover
    asyncio.run(main())
