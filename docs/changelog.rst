Changelog for ``igbpyutils``
============================

Changelog
---------

v0.9.0 - *not yet released*
    - ...

v0.8.0 - Fri Oct 11 2024
    - **REMOVED** ``gen-coveragerc`` and **deprecated** :func:`~igbpyutils.dev.generate_coveragerc`
        - Use https://pypi.org/project/coverage-simple-excludes/ instead.
    - **Renamed** ``igbpyutils.dev.check_script_vs_lib`` to :func:`igbpyutils.dev.script_vs_lib.check_script_vs_lib`
        - The former is still available but raises a deprecation warning. (*Update:* Warning was not yet implemented in this release)
        - The ``known_shebangs`` argument may now be a regular expression.
        - The ``exec_from_git`` option now uses the current index instead of the tree,
          so uncommitted changes are correctly seen.

v0.7.0 - Sun Oct  6 2024
    - Added :class:`~igbpyutils.error.LoggingStream` for better type checking
      on :func:`igbpyutils.error.logging_config`.
    - Added :func:`igbpyutils.file.open_out`.
    - ``igbpyutils.dev.check_script_vs_lib`` allows more shebangs by default.

v0.6.0 - Mon Jun 17 2024
    - Added :func:`~igbpyutils.file.simple_cache`.

v0.5.0 - Sat Mar 30 2024
    - **REMOVED** ``simple-perms`` and **deprecated** :func:`~igbpyutils.file.simple_perms`
        - Use https://pypi.org/project/simple-perms/ instead.
    - **Deprecated** :func:`igbpyutils.iter.is_unique_everseen`
        - Use :func:`more_itertools.classify_unique` instead.
    - Added ``cover-OS`` tags to :func:`~igbpyutils.dev.generate_coveragerc`

v0.4.1 - Sun Dec 10 2023
    - Fix :func:`~igbpyutils.file.cmdline_rglob` on empty generator

v0.4.0 - Sun Dec 10 2023
    - Changed :func:`~igbpyutils.file.autoglob` to detect current shell
      via environment variables instead of ``sys.platform``
    - Added :func:`igbpyutils.dev.generate_coveragerc` and CLI
    - Added and used :func:`igbpyutils.file.cmdline_rglob`
        - *Note:* This changes the behavior of the command-line tools included in
          this project slightly in that a directory specified on the command line
          is now also processed, instead of just its contents.

v0.3.2 - Thu Nov  2 2023
    - Added ``--add*`` options to ``simple-perms`` tool

v0.3.1 - Sun Oct  8 2023
    - Fixed project requirements

v0.3.0 - Wed Oct  4 2023
    - Added ``exec_from_git`` option to ``igbpyutils.dev.check_script_vs_lib``
    - Added :func:`~igbpyutils.file.simple_perms`

v0.2.0 - Sun Sep 24 2023
    - Added :class:`igbpyutils.error.CustomFormatter` and :func:`igbpyutils.error.logging_config`
    - Added custom :func:`threading.excepthook` to :class:`~igbpyutils.error.CustomHandlers`
    - Added :func:`igbpyutils.error.asyncio_exception_handler`
      (also added to :class:`~igbpyutils.error.CustomHandlers`)

v0.1.0 - Tue Sep 19 2023
    - Added :mod:`igbpyutils.dev`

v0.0.9 - Sat Aug 19 2023
    - Added :func:`igbpyutils.file.replace_link`

v0.0.8 - Tue Jul  4 2023
    - Fixed changelog

v0.0.7 - Tue Jul  4 2023
    - Added :class:`igbpyutils.file.BinaryStream`

v0.0.6 - Wed May  3 2023
    - Minor tweak to documentation generation only

v0.0.5 - Wed May  3 2023
    - Documentation updates only

v0.0.4 - Wed May  3 2023
    - Exposed a few more functions in the :mod:`igbpyutils.error` API

v0.0.3 - Sun Apr 16 2023
    - Added :mod:`igbpyutils.dt`

v0.0.2 - Sat Apr 15 2023
    - Added :mod:`igbpyutils.error`

v0.0.1 - Fri Apr 14 2023
    - First release.

Note this changelog covers user-visible changes only, internal changes
such as for testing are not listed, and not all documentation updates.

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

