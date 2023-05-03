# Configuration file for the Sphinx documentation builder.
from pathlib import Path
import sys
import tomllib
sys.path.insert(0, str(Path(__file__).parent.parent.resolve(strict=True)))

# ### Munging Code ###
def generate():
    from importlib import import_module
    """This generates a ``.rst`` file for each module. Apparently, autodoc will put the
    module's docstring, which includes the title, at the same indentation level as the
    members. To work around that, here we take the module's docstring and munge it
    to generate the ``.rst`` file. Below, we suppress the docstring from being output
    as part of the autodoc output."""
    for file in (Path(__file__).parent.parent/'igbpyutils').iterdir():
        if file.suffix == '.py' and not file.name=='__init__.py':
            rf = Path(__file__).parent/(file.stem + '.rst')
            doc = import_module('igbpyutils.'+file.stem).__doc__
            (before, copy1, copy) = doc.partition('Author, Copyright, and License')
            (title, _, desc) = before.partition("\n\n")
            before = title + "\n" + ("="*len(title)) + "\n\n" + desc
            auto = f".. automodule:: igbpyutils.{file.stem}\n   :members:\n   :undoc-members:\n\n"
            after = copy1 + copy
            with rf.open('w') as fh:
                print(before + auto + after, file=fh)
generate()  # in a function so we don't pollute the global namespace
def process_docstring(app, what, name, obj, options, lines :list[str]):
    if what=='module': lines.clear()
    return True
def setup(app):
    app.connect('autodoc-process-docstring', process_docstring)

# ### Configuration ###
project = 'igbpyutils'
author = 'Hauke D'
copyright = '2023 Hauke Daempfling at the IGB'
with (Path(__file__).parent.parent/'pyproject.toml').open('rb') as fh:
    version = tomllib.load(fh)['project']['version']

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.viewcode']

nitpicky = True
nitpick_ignore_regex = [
    ('py:class', '\\A.*\\._[TV]\\Z'),  # generics
]

autodoc_member_order = 'bysource'

html_static_path = ["_static"]
html_theme = 'furo'
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#819F00",
        "color-brand-content": "#003D72",
        "color-api-name": "#003D72",
        "color-api-pre-name": "#003D72",
    },
    "dark_css_variables": {
        "color-brand-primary": "#9DBD15",
        "color-brand-content": "#006EB7",
        "color-api-name": "#006EB7",
        "color-api-pre-name": "#006EB7",
    },
    "light_logo": "IGB_farbe_pos.svg",
    "dark_logo": "IGB_farbe_neg.svg",
}
pygments_style = "sphinx"
pygments_dark_style = "monokai"

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'more-itertools': ('https://more-itertools.readthedocs.io/en/stable/', None),
}
