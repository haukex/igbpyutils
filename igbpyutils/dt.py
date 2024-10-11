"""Datetime Utility Functions

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
from datetime import timedelta

def timedelta_str(td :timedelta) -> str:
    """Simple replacement for the :class:`~datetime.timedelta` default string formatting with nicer output of negative deltas.

        >>> str(timedelta(hours=-1))
        '-1 day, 23:00:00'
        >>> timedelta_str(timedelta(hours=-1))
        '-1:00:00'

    Possible alternatives:

    * https://dateutil.readthedocs.io/en/stable/relativedelta.html
    * https://pypi.org/project/readabledelta/
    """
    return '-' + str(-td) if td < timedelta(0) else str(td)

#TODO Later: datetime truncate
#TODO Later: datetime fromisoformat (backport support for Z suffix)
