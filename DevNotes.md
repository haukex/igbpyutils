Internal Development Notes
--------------------------

Documentation
-------------

- <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>
- <https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#cross-referencing-python-objects>
- TODO: <https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists>

Making a Release
----------------

- Update `docs/changelog.rst`
- Update version number everywhere
- `git commit`
- `git push`
- Wait for tests on GitHub to pass
- `git tag vX.X.X`
- `git push --tags`
- `python3 -m build`
- `twine upload dist/igbpyutils-*.tar.gz`
- Add new release on GitHub
