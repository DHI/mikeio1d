"""LibraryLoader class."""

import clr
from pathlib import Path
from warnings import warn


class LibraryLoader:
    """Helper class which assigns 'load_[LIRABRY_NAME]' to MIKE.NET module.

    Parameters
    ----------
    file_name: str
        Library file_name to load. Typically this is a full path to the library (dll).
    mikenet_module: module
        Reference to MIKET.NET module

    """

    def __init__(self, file_name, mikenet_module):
        self.file_name = file_name
        self.mikenet_module = mikenet_module

        self.file_path = Path(file_name)
        self.library_name = self.file_path.stem
        self.library_alias = self.library_name.replace("DHI.", "")
        self.library_alias = self.library_alias.replace(".", "_")

        load_function_name = "load_" + self.library_alias

        setattr(mikenet_module, load_function_name, self.load)

    def load(self):
        """Add a reference of a relevant library to Python.NET (CLR) and also add a reference to the MIKE.NET."""
        clr.AddReference(self.library_name)

        try:
            mikenet_dict = self.mikenet_module.__dict__
            exec(f"import {self.library_name} as {self.library_alias}", mikenet_dict)
        except Exception as e:
            warn(f"Could not import .NET library {self.library_name}: {e}")
