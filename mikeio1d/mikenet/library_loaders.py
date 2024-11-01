"""Module for loading MIKE software .NET libraries."""

import os
import sys
from glob import glob

from ..mikepath import MikePath

from .library_loader import LibraryLoader


class LibraryLoaders:
    """Helper class which finds all MIKE software .NET libraries and assigns references to those libraries in MIKE.NET module.

    Parameters
    ----------
    mikenet_module: module
        Reference to MIKE.NET module

    """

    def __init__(self, mikenet_module):
        self.mikenet_module = mikenet_module
        self.library_loader_list = []
        self.library_loader_dict = {}

        MikePath.setup_mike_installation(sys.path)
        self.create_loaders()

    def create_loaders(self):
        """Create .NET library loaders and assigns relevant `load` methods to MIKE.NET module."""
        mikenet_module = self.mikenet_module

        for pattern in MikePath.library_patterns:
            file_candidates = glob(os.path.join(MikePath.mike_bin_path, pattern))
            for file_name in file_candidates:
                library_loader = LibraryLoader(file_name, mikenet_module)
                self.library_loader_list.append(library_loader)
                self.library_loader_dict[library_loader.library_name] = library_loader
                self.library_loader_dict[library_loader.library_alias] = library_loader

        setattr(mikenet_module, "load_all", self.load_all)
        setattr(mikenet_module, "load", self.load)

    def load_all(self):
        """Load all libraries present in library_loader_list."""
        for library_loader in self.library_loader_list:
            library_loader.load()

    def load(self, libraries=[]):
        """Load all libraries specified by the list `libraries`.

        Parameters
        ----------
        libraries: list of str
            List of strings specifying what .NET libraries to load.
            This can also be set as a string having the name of the
            library to load.

        """
        if isinstance(libraries, str):
            libraries = [libraries]

        for library in libraries:
            self.library_loader_dict[library].load()
