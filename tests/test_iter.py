"""Tests for ``igbpyutils.iter``.

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
import warnings
from more_itertools import classify_unique
from igbpyutils.iter import no_duplicates, SizedCallbackIterator, is_unique_everseen, zip_strict

class TestIterTools(unittest.TestCase):

    def test_zip_strict(self):
        l2 = [0, 1]
        l3 = [2, 3, 4]
        l3b = [5, 6, 7]
        l4 = [8, 9, 10, 11]
        self.assertEqual( list(zip_strict(l3, l3b)), list(zip(l3, l3b)) )
        with self.assertRaises(ValueError):
            list( zip_strict( l2, l3, l4 ) )
        with self.assertRaises(ValueError):
            list( zip_strict( l2, l2, l4, l4 ) )

    def test_sized_cb_iterator(self):
        def gen(x):
            yield from range(x)
        g = gen(10)
        with self.assertRaises(TypeError):
            self.assertNotEqual(len(g), 10)  # pyright: ignore [reportArgumentType]
        cbvals = []
        it = SizedCallbackIterator(g, 10, callback=lambda *a: cbvals.append(a))
        self.assertEqual(len(it), 10)
        self.assertEqual(iter(it), it)
        self.assertEqual(list(it), [0,1,2,3,4,5,6,7,8,9])
        self.assertEqual(cbvals, [(0,0), (1,1), (2,2), (3,3), (4,4), (5,5), (6,6), (7,7), (8,8), (9,9)])
        with self.assertRaises(ValueError):
            SizedCallbackIterator(range(1), -1)
        # strict on
        self.assertEqual(
            list(SizedCallbackIterator(gen(10), 10, strict=True)),
            [0,1,2,3,4,5,6,7,8,9] )
        with self.assertRaises(ValueError):
            list(SizedCallbackIterator(gen(10), 11, strict=True))
        with self.assertRaises(ValueError):
            list(SizedCallbackIterator(gen(10), 9, strict=True))
        # another callback test
        def gen2(x):
            for i in range(x):
                yield chr(ord('a') + i) * (i+1)
        cbvals.clear()
        it2 = SizedCallbackIterator(gen2(6), 6, callback=lambda *a: cbvals.append(a))
        self.assertEqual(len(it2), 6)
        self.assertEqual(list(it2), ['a', 'bb', 'ccc', 'dddd', 'eeeee', 'ffffff'])
        self.assertEqual(cbvals, [(0,'a'), (1,'bb'), (2,'ccc'), (3,'dddd'), (4,'eeeee'), (5,'ffffff')] )

    def test_is_unique_everseen(self):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            # taken from more-itertools docs
            self.assertEqual( tuple(is_unique_everseen('mississippi')),
                              (True,True,True,False,False,False,False,False,True,False,False) )
            self.assertEqual( tuple(is_unique_everseen('AaaBbbCccAaa', key=str.lower)),
                              (True,False,False,True,False,False,True,False,False,False,False,False) )
            self.assertEqual( tuple(is_unique_everseen('AAAABBBCCDAABBB')),
                              (True,False,False,False,True,False,False,True,False,True,False,False,False,False,False) )
            self.assertEqual( tuple(is_unique_everseen('ABBcCAD', key=str.lower)),
                              (True,True,False,True,False,False,True) )
            # taken from test_no_duplicates below
            self.assertEqual( tuple(is_unique_everseen( ( "foo", "bar", "quz", 123 ) )),
                              (True,True,True,True) )
            self.assertEqual( tuple(is_unique_everseen( [ "foo", ["bar", "quz"] ] )),
                              (True,True) )
            self.assertEqual( tuple(is_unique_everseen( ("foo", 123, "bar", "foo") )),
                              (True,True,True,False) )
            self.assertEqual( tuple(is_unique_everseen( ("foo", "bar", "quz", "Foo"), key=str.lower )),
                              (True,True,True,False) )
            self.assertEqual( tuple(is_unique_everseen([ ["foo","bar"], "quz", ["quz"], ["foo","bar"], "quz" ])),
                              (True,True,True,False,False) )

    def test_no_duplicates(self):
        in1 = ( "foo", "bar", "quz", 123 )
        self.assertEqual( tuple(no_duplicates(in1)), in1 )
        in2 = [ "foo", ["bar", "quz"] ]
        self.assertEqual( list(no_duplicates(in2)), in2 )
        with self.assertRaises(ValueError):
            tuple(no_duplicates( ("foo", 123, "bar", "foo") ))
        with self.assertRaises(ValueError):
            set(no_duplicates( ("foo", "bar", "quz", "Foo"), key=str.lower ))
        with self.assertRaises(ValueError):
            list(no_duplicates( [ ["foo","bar"], "quz", ["quz"], ["foo","bar"] ] ))
        # documented alternative to no_duplicates if one doesn't need the return values:
        #self.assertFalse( not all(is_unique_everseen((1,2,3))) )
        #self.assertTrue( not all(is_unique_everseen((1,2,3,1))) )
        self.assertFalse( not all( ever for _e,_just,ever in classify_unique((1,2,3)  ) ) )
        # the "[]" in the following is required to avoid coverage complaining "didn't finish the generator expression"
        # perhaps related:
        # https://github.com/nedbat/coveragepy/issues/475
        # https://github.com/nedbat/coveragepy/issues/1333
        lst = [ ever for _e,_just,ever in classify_unique((1,2,3,1)) ]
        self.assertTrue( not all( lst ) )
