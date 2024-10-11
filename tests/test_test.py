"""Tests for ``igbpyutils.test``.

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
import unittest
from igbpyutils.test import tempcopy

class TestTestUtils(unittest.TestCase):

    def test_tempcopy(self):
        obj :dict = { "hello":"world", "foo":[1,2.3,True,None] }
        with tempcopy(obj) as o2:
            self.assertIsNot( obj, o2 )
            self.assertIsNot( obj['foo'], o2['foo'] )
            o2['foo'][0] = "bar"
            self.assertEqual( o2, { "hello":"world", "foo":["bar",2.3,True,None] } )
            self.assertEqual( obj, { "hello":"world", "foo":[1,2.3,True,None] } )
        self.assertEqual( obj, { "hello":"world", "foo":[1,2.3,True,None] } )
