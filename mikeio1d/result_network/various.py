"""Various helper functions for the result network module."""

from __future__ import annotations
import re
from typing import List, Tuple, Dict
from html import escape


class ValidPythonIdentifierTranslatorTable:
    """Translator table for replacing invalid python characters with a valid identifier.

    Used as argument to Python's built-in str.translate() method.

    Parameters
    ----------
    replacement : str, default = "_"
       The character to replace invalid characters with.

    """

    def __init__(self, replacement="_"):
        self.replacement = replacement

    def __getitem__(self, key):
        """Return the replacement character if the key is not a valid python identifier character."""
        key = chr(key)
        if key.isdigit() or key.isidentifier():
            return key
        else:
            return self.replacement


_translator_table = ValidPythonIdentifierTranslatorTable()


def make_proper_variable_name(string: str, extra_string_before_digit="_"):
    """Make a more proper variable name.

    It is assumed that the input string never is or after manipulations
    becomes an '_' or an empty string.
    """
    # Replace all characters that are not valid python identifier by an underscore.
    string = string.translate(_translator_table)
    # Replace more than two underscores with a single underscore.
    string = re.sub(r"_{2,}", "_", string)
    # Remove a starting underscore
    if len(string) > 1:
        string = string[1:] if string[0] == "_" else string
    # Remove a trailing underscore
    if len(string) > 1:
        string = string[:-1] if string[-1] == "_" else string
    # Add an extra string if the string starts with a number.
    string = extra_string_before_digit + string if string and string[0].isdigit() else string
    return string


def build_html_repr_from_sections(header: str, sections: List[Tuple[str, List | Dict]]):
    """Build an html representation from a list of sections.

    Parameters
    ----------
    header : str
        Header string (e.g. <ResultNode>).
    sections : list of tuples
        List of tuples with section name and section content.
        The section content can be either a list of values or
        a dictionary of key value pairs.

    """
    repr = escape(header)
    repr += _build_html_repr_section_style()  # TODO: A better way to inject css?
    for section_name, section_content in sections:
        if isinstance(section_content, list):
            section = _build_html_repr_section_from_list(section_name, section_content)
        elif isinstance(section_content, dict):
            section = _build_html_repr_section_from_dict(section_name, section_content)
        else:
            raise ValueError(f"Unknown section content type: {section_content}")
        repr += section
    return repr


def _build_html_repr_section_style():
    """Build a style string for html representation."""
    style = """
    <style>
        ul {
            margin: 0px;
            padding: 0px;
            padding-left: 2em;
        }
    </style>
    """
    return style


def _build_html_repr_section_from_dict(name, keyvalues):
    """Build a section from a dictionary."""
    section = "<details>"
    section += f"<summary>{name}</summary>"
    section += "<ul>"
    for key, value in keyvalues.items():
        section += f"<li>{key}: {value}</li>"
    section += "</ul>"
    section += "</details>"
    return section


def _build_html_repr_section_from_list(name, values):
    """Build a section from a list."""
    section = "<details>"
    section += f"<summary>{name}</summary>"
    section += "<ul>"
    for value in values:
        section += f"<li>{value}</li>"
    section += "</ul>"
    section += "</details>"
    return section
