"""MIKE.NET: Module for loading MIKE software .NET libraries.

MIKE.NET is a module which creates helper methods for loading and referencing
MIKE software .NET libraries. To use the module on an existing MIKE installation
one needs before loading MIKE IO 1D to define `MIKE_INSTALL_PATH` environment
variable which points to desired installation:

```python
>>> import os
>>> os.environ["MIKE_INSTALL_PATH"] = "C:/Program File (x86)/DHI/MIKE+/2023/"
```

If this variable is not defined the MIKE IO 1D bin folder will be used per
default. This MIKE IO 1D bin folder contains very small subset of MIKE software
libraries.

Usage example
-------------

MIKE.NET can be imported as:

```python
>>> from mikeio1d import mikenet
```

When used within Jupyter `mikenet` has a list of methods starting with `load_`
which can load the relevant MIKE software libraries. For example, we can load a
`DHI.Mike1D.Generic` library as:

```python
>>> mikenet.load_Mike1D_Generic()
```

This makes a `Mike1D_Generic` reference to the `DHI.Mike1D.Generic`, which also
can be auto-completed in Jupyter. As an example, now we can create an instance
of `Quantity` class as:

```python
>>> quantity = mikenet.Mike1D_Generic.Quantity()
```

To load all MIKE software libraries one can use:

```python
>>> mikenet.load_all()
```
"""

import sys

from .library_loaders import LibraryLoaders

mikenet_module = sys.modules[__name__]
library_loaders = LibraryLoaders(mikenet_module)
