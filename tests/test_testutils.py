#!/usr/bin/env python3
"""Tests for testutils.

Author, Copyright, and License
------------------------------
Copyright (c) 2023 Hauke Daempfling (haukex@zero-g.net)
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
import sys
from testutils import tempcopy, MyNamedTempFile
from pathlib import Path
from tempfile import NamedTemporaryFile

class TestTestUtils(unittest.TestCase):

    def test_mynamedtempfile(self):
        with NamedTemporaryFile() as tf1:
            tf1.write(b'Foo')
            tf1.close()
            self.assertFalse( Path(tf1.name).exists() )
        with MyNamedTempFile() as tf2:
            tf2.write(b'Bar')
            tf2.close()
            self.assertTrue( Path(tf2.name).exists() )
        self.assertFalse( Path(tf2.name).exists() )
        if sys.hexversion>=0x030C00F0:  # pragma: no cover
            # noinspection PyArgumentList
            with NamedTemporaryFile(delete=True, delete_on_close=False) as tf3:
                tf3.write(b'Quz')
                tf3.close()
                self.assertTrue( Path(tf3.name).exists() )
            self.assertFalse( Path(tf3.name).exists() )

    def test_tempcopy(self):
        obj = { "hello":"world", "foo":[1,2.3,True,None] }
        with tempcopy(obj) as o2:
            self.assertIsNot( obj, o2 )
            self.assertIsNot( obj['foo'], o2['foo'] )
            # noinspection PyTypeChecker
            o2['foo'][0] = "bar"
            self.assertEqual( o2, { "hello":"world", "foo":["bar",2.3,True,None] } )
            self.assertEqual( obj, { "hello":"world", "foo":[1,2.3,True,None] } )
        self.assertEqual( obj, { "hello":"world", "foo":[1,2.3,True,None] } )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
