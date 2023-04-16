#!/usr/bin/env python3
"""Tests for ``igbpyutils.iter``.

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
import unittest
from itertools import product
from more_itertools import gray_product
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

    def test_unzip_zip(self):
        """Make sure that ``unzip``-then-``zip`` works as expected,
        that is, it consumes the input table one row at a time.

        It is documented that ``unzip`` uses ``tee`` internally, and this should
        hopefully confirm that its internal storage doesn't grow too large."""
        from more_itertools import unzip
        totest = []
        def gen():
            tbl = (
                ("One", "Abc", "Foo"),
                ("Two", "Def", "Bar"),
                ("Thr", "Ghi", "Quz"),
            )
            for row in tbl:
                totest.append(f"gen {row!r}")
                yield row
        def trans(seq, start):
            for i, x in enumerate(seq, start=start):
                totest.append(f"trans {x}")
                yield x.lower()+str(i)
        for orow in zip_strict( *( trans(col, ci*3) for ci, col in enumerate(unzip(gen())) ) ):
            totest.append(f"got {orow!r}")
        self.assertEqual([
            "gen ('One', 'Abc', 'Foo')", 'trans One', 'trans Abc', 'trans Foo', "got ('one0', 'abc3', 'foo6')",
            "gen ('Two', 'Def', 'Bar')", 'trans Two', 'trans Def', 'trans Bar', "got ('two1', 'def4', 'bar7')",
            "gen ('Thr', 'Ghi', 'Quz')", 'trans Thr', 'trans Ghi', 'trans Quz', "got ('thr2', 'ghi5', 'quz8')",
        ], totest)
        # check that an unequal number of columns throws an error
        tbl2 = ((0, "x", "y"), (1, "a"))
        with self.assertRaises(ValueError):
            tuple( zip_strict( *( tuple(x) for x in unzip(tbl2) ) ) )

    def test_tee_zip(self):
        """Make sure that the ``tee``-then-``zip`` pattern works as expected,
        that is, that it really does consume the input one-at-a-time."""
        from itertools import tee
        totest = []
        def gen():
            for x in range(1,4):
                totest.append(f"gen {x}")
                yield x
        def trans(seq):
            for x in seq:
                out = chr( x + ord('A') - 1 )
                totest.append(f"trans {x}-{out}")
                yield out
        g1, g2 = tee(gen())
        for i, o in zip_strict(g1, trans(g2)):
            totest.append(f"got {i}-{o}")
        self.assertEqual( totest, [
            'gen 1', 'trans 1-A', 'got 1-A',
            'gen 2', 'trans 2-B', 'got 2-B',
            'gen 3', 'trans 3-C', 'got 3-C'] )

    def test_gray_product(self):
        # gray_product has been merged into more_itertools, but we'll keep this test here for now anyway
        self.assertEqual( tuple( gray_product( ('a','b','c'), range(1,3) ) ),
            ( ("a",1), ("b",1), ("c",1), ("c",2), ("b",2), ("a",2) ) )

        out = gray_product(('foo', 'bar'), (3, 4, 5, 6), ['quz', 'baz'])
        self.assertEqual(next(out), ('foo', 3, 'quz'))
        self.assertEqual(list(out), [
            ('bar', 3, 'quz'), ('bar', 4, 'quz'), ('foo', 4, 'quz'), ('foo', 5, 'quz'), ('bar', 5, 'quz'),
            ('bar', 6, 'quz'), ('foo', 6, 'quz'), ('foo', 6, 'baz'), ('bar', 6, 'baz'), ('bar', 5, 'baz'),
            ('foo', 5, 'baz'), ('foo', 4, 'baz'), ('bar', 4, 'baz'), ('bar', 3, 'baz'), ('foo', 3, 'baz')])

        self.assertEqual( tuple( gray_product() ), ((), ) )
        self.assertEqual( tuple( gray_product( (1,2) ) ), ( (1,), (2,) ) )
        with self.assertRaises(ValueError): list( gray_product( (1,2), () ) )
        with self.assertRaises(ValueError): list( gray_product( (1,2), (2,) ) )

        iters = ( ("a","b"), range(3,6), [None, None], {"i","j","k","l"}, "XYZ" )
        self.assertEqual( sorted( product(*iters) ), sorted( gray_product(*iters) ) )

    def test_sized_cb_iterator(self):
        def gen(x):
            for i in range(x): yield i
        g = gen(10)
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            self.assertNotEqual(len(g), 10)
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
            for i in range(x): yield chr(ord('a') + i) * (i+1)
        cbvals.clear()
        it2 = SizedCallbackIterator(gen2(6), 6, callback=lambda *a: cbvals.append(a))
        self.assertEqual(len(it2), 6)
        self.assertEqual(list(it2), ['a', 'bb', 'ccc', 'dddd', 'eeeee', 'ffffff'])
        self.assertEqual(cbvals, [(0,'a'), (1,'bb'), (2,'ccc'), (3,'dddd'), (4,'eeeee'), (5,'ffffff')] )

    def test_is_unique_everseen(self):
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
        # alternative to no_duplicates if one doesn't need the return values:
        self.assertFalse( not all(is_unique_everseen((1,2,3))) )
        self.assertTrue( not all(is_unique_everseen((1,2,3,1))) )

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

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
