"""Tests for some iterator patterns.

This test does not actually test any functions in this package,
it is simply here to confirm that certain patterns work the way
I expect across various versions of Python and OSes (and also
to see if any regressions might happen in the future).

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
from typing import Any
from itertools import tee, product
from collections.abc import Generator, Iterable
from more_itertools import unzip, gray_product
from igbpyutils.iter import zip_strict

class TestIterPatterns(unittest.TestCase):

    def test_unzip_zip(self):
        """Make sure that ``unzip``-then-``zip`` works as expected,
        that is, it consumes the input table one row at a time.

        It is documented that ``unzip`` uses ``tee`` internally, and this should
        hopefully confirm that its internal storage doesn't grow too large."""
        totest = []
        def gen() -> Generator[tuple[str, str, str], None, None]:
            tbl = (
                ("One", "Abc", "Foo"),
                ("Two", "Def", "Bar"),
                ("Thr", "Ghi", "Quz"),
            )
            for row in tbl:
                totest.append(f"gen {row!r}")
                yield row
        def trans(seq :Iterable[Any], start :int) -> Generator[str, None, None]:
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

    def test_transpose(self):
        """Test to confirm the difference between ``zip(*iter)`` and ``unzip(iter)``.

        :func:`zip` reads the entire iterable and produces tuples, while :func:`more_itertools.unzip`
        produces iterators using :func:`itertools.tee` - but note that since this also buffers items,
        it can also use significant memory."""
        totest = []
        def gen() -> Generator[tuple[str, str, str], None, None]:
            tbl = (
                ("One", "Abc", "Foo"),
                ("Two", "Def", "Bar"),
                ("Thr", "Ghi", "Quz"),
            )
            for row in tbl:
                totest.append(f"gen {row!r}")
                yield row
        for t1 in zip_strict(*gen()):
            self.assertIsInstance(t1, tuple)
            totest.append(f"got {t1!r}")
        expect = [
            "gen ('One', 'Abc', 'Foo')", "gen ('Two', 'Def', 'Bar')", "gen ('Thr', 'Ghi', 'Quz')",
            "got ('One', 'Two', 'Thr')", "got ('Abc', 'Def', 'Ghi')", "got ('Foo', 'Bar', 'Quz')",
        ]
        self.assertEqual(totest, expect)
        totest = []
        for t2 in unzip(gen()):
            self.assertIsInstance(t2, map)
            totest.append(f"got {tuple(t2)!r}")
        self.assertEqual(totest, expect)

    def test_tee_zip(self):
        """Make sure that the ``tee``-then-``zip`` pattern works as expected,
        that is, that it really does consume the input one-at-a-time.
        **However**, see the "better variant" in the code below!!"""
        totest = []
        def gen() -> Generator[int, None, None]:
            for x in range(1,4):
                totest.append(f"gen {x}")
                yield x
        def trans(seq :Iterable[int]) -> Generator[str, None, None]:
            for x in seq:
                out = chr( x + ord('A') - 1 )
                totest.append(f"trans {x}-{out}")
                yield out
        g1, g2 = tee(gen())
        # Note the +3 (and +4 below) is to see if passing a modified sequence through works as well,
        # `trans(g2)` should work fine too; parallel to `trans( i := x for x in gen() )` below.
        for i, o in zip_strict(g1, trans( y+3 for y in g2 )):
            totest.append(f"got {i}-{o}")
        self.assertEqual( totest, [
            'gen 1', 'trans 4-D', 'got 1-D',
            'gen 2', 'trans 5-E', 'got 2-E',
            'gen 3', 'trans 6-F', 'got 3-F'] )
        totest.clear()
        # The better variant by Stefan Pochmann at https://stackoverflow.com/a/76271631
        # (the only minor downside being that PyChram detects "i" as "referenced before assignment")
        for o in trans( (i := x)+4 for x in gen() ):
            totest.append(f"got {i}-{o}")
        self.assertEqual( totest, [
            'gen 1', 'trans 5-E', 'got 1-E',
            'gen 2', 'trans 6-F', 'got 2-F',
            'gen 3', 'trans 7-G', 'got 3-G'] )

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
        with self.assertRaises(ValueError):
            list( gray_product( (1,2), () ) )
        with self.assertRaises(ValueError):
            list( gray_product( (1,2), (2,) ) )

        iters = ( ("a","b"), range(3,6), [None, None], {"i","j","k","l"}, "XYZ" )
        self.assertEqual( sorted( product(*iters) ), sorted( gray_product(*iters) ) )
