"""Tests for ``igbpyutils.dt``.

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
import unittest
from datetime import timedelta
from igbpyutils.dt import timedelta_str

class TestDateTimeUtils(unittest.TestCase):

    def test_timedelta_str(self):
        td5m = timedelta( minutes=5 )
        self.assertEqual( str(td5m), "0:05:00" )
        self.assertEqual( str(-td5m), "-1 day, 23:55:00" )
        self.assertEqual( timedelta_str(td5m), "0:05:00" )
        self.assertEqual( timedelta_str(-td5m), "-0:05:00" )
        td10h = timedelta( hours=10, minutes=23, seconds=45 )
        self.assertEqual( str(td10h), "10:23:45" )
        self.assertEqual( str(-td10h), "-1 day, 13:36:15" )
        self.assertEqual( timedelta_str(td10h), "10:23:45" )
        self.assertEqual( timedelta_str(-td10h), "-10:23:45" )
        td3d = timedelta( days=3, hours=1, minutes=2, seconds=3 )
        self.assertEqual( str(td3d), "3 days, 1:02:03" )
        self.assertEqual( str(-td3d), "-4 days, 22:57:57" )
        self.assertEqual( timedelta_str(td3d), "3 days, 1:02:03" )
        self.assertEqual( timedelta_str(-td3d), "-3 days, 1:02:03" )
