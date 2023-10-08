Internal Development Notes
--------------------------

TODO: <https://mypy.readthedocs.io/en/stable/stubgen.html>

Documentation
-------------

- <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>
- <https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#cross-referencing-python-objects>
- TODO: <https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists>

Making a Release
----------------

- Update `docs/changelog.rst`
- Update version number everywhere (e.g. `grep -r '0\.[0-9]\.[0-9]'`)
- Try building the docs (`make clean all` in `docs` subdir)
- `git commit`
- `git push`
- Wait for tests on GitHub to pass
- Check <https://readthedocs.org/projects/igbpyutils/> to make sure docs are building there
	- TODO: Consider <https://github.com/actions/deploy-pages> instead
- `git tag vX.X.X`
- `git push --tags`
- (The following steps should be done on Linux)
- `python3 -m build`
- Optional: inspect the package with `tar tzvf dist/igbpyutils-*.tar.gz`
- Run `dev/isolated_test.sh dist/igbpyutils-*.tar.gz`
- `twine upload dist/igbpyutils-*.tar.gz`
- Add new release on GitHub
- `git clean -dxf dist *.egg-info`
- Optional: Add placeholder for next version to changelog
- Test installation of package and command-line scripts
