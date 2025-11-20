Error Handling and Formatting Utilities
=======================================

Overview
--------

This module primarily provides :func:`~igbpyutils.error.javaishstacktrace` and a custom version of
:func:`warnings.showwarning`, both of which produce somewhat shorter messages than the default Python messages.
They can be set up via the context manager :class:`~igbpyutils.error.CustomHandlers` or, more typically, via a
call to :func:`~igbpyutils.error.init_handlers` at the beginning of the script.
This module also provides :func:`~igbpyutils.error.logging_config` for configuration of :mod:`logging`.

Functions
---------

.. automodule:: igbpyutils.error
   :members:
   :undoc-members:

Author, Copyright, and License
------------------------------
Copyright (c) 2022-2025 Hauke Daempfling (haukex@zero-g.net)
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

