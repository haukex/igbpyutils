Development Notes
=================

Identical to <https://github.com/haukex/my-py-templ/blob/main/dev/DevNotes.md> except:
- Documentation:
  - Requires Python 3.10! (e.g. `. ~/.venvs/igbpyutils/.venv3.10/bin/activate`)
  - Build deps: `( cd docs && make installdeps )`
  - The changelog is at `docs/changelog.rst`
  - Build: `( cd docs && make clean all )`,
    but the actual documentation is built on *Read the Docs*
  - Check <https://readthedocs.org/projects/igbpyutils/> to make sure docs are building there
  - `git clean -dxf docs/html`
