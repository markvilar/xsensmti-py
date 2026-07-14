"""
MkDocs hook that exposes the installed xsensmti version to the documentation.

Reads the version from the installed package rather than parsing pyproject.toml,
so the documentation cannot drift from the library it documents. Markdown pages
may reference it as `{{ library_version }}`.
"""

from importlib.metadata import version
from typing import Any

_LIBRARY_VERSION: str = version("xsensmti")

_PLACEHOLDER: str = "{{ library_version }}"


def on_config(config: Any) -> Any:
    """Expose the version to templates and show it in the site footer."""
    config.extra["library_version"] = _LIBRARY_VERSION
    config.copyright = f"xsensmti {_LIBRARY_VERSION}"
    return config


def on_page_markdown(markdown: str, **kwargs: Any) -> str:
    """Substitute the version placeholder in page content."""
    return markdown.replace(_PLACEHOLDER, _LIBRARY_VERSION)
