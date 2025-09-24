"""Configuration file for the Sphinx documentation builder."""

import os
import sys
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath('../src'))

# -- Project information -----------------------------------------------------

project = 'MCP Ticketer'
copyright = f'{datetime.now().year}, MCP Ticketer Team'
author = 'MCP Ticketer Team'

# Import version from package
try:
    from mcp_ticketer import __version__
    release = __version__
    version = '.'.join(release.split('.')[:2])  # Major.minor version
except ImportError:
    release = '0.1.0'
    version = '0.1'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
    'sphinx_click',
    'myst_parser',
]

# Add any paths that contain templates here
templates_path = ['_templates']

# List of patterns to exclude from source files
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix of source filenames
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master toctree document
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': True,
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

html_static_path = ['_static']
html_logo = None  # Add logo if available
html_favicon = None  # Add favicon if available

# -- Options for autodoc -----------------------------------------------------

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

autodoc_typehints = 'description'
autodoc_mock_imports = []

# -- Options for autosummary -------------------------------------------------

autosummary_generate = True
autosummary_imported_members = True

# -- Options for intersphinx -------------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pydantic': ('https://docs.pydantic.dev/', None),
    'typer': ('https://typer.tiangolo.com/', None),
    'httpx': ('https://www.python-httpx.org/', None),
}

# -- Options for Napoleon ----------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# -- Options for MyST --------------------------------------------------------

myst_enable_extensions = [
    "deflist",
    "tasklist",
    "html_image",
    "colon_fence",
    "smartquotes",
    "replacements",
    "linkify",
    "strikethrough",
]

myst_heading_anchors = 3

# -- Options for sphinx-click ------------------------------------------------

click_log_level = "INFO"

# -- Custom configuration ----------------------------------------------------

# Add custom CSS/JS if needed
def setup(app):
    app.add_css_file('custom.css')  # Optional custom CSS
    app.add_js_file('custom.js')  # Optional custom JS