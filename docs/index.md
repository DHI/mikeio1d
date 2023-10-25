![](../images/logo/MIKE-IO-1D-Logo-Pos-RGB-nomargin.png)

# Welcome to MIKE IO 1D's documentation!
 ![Python version](https://img.shields.io/pypi/pyversions/mikeio1d.svg)
[![PyPI version](https://badge.fury.io/py/mikeio1d.svg)](https://badge.fury.io/py/mikeio1d)

Read res1d and xns11 files.

For other MIKE files (dfs0, dfs1, dfs2, dfsu, and mesh files) use the related package [MIKE IO](https://github.com/DHI/mikeio)

```{note} MIKE IO 1D is under development and could be subject to changes.
```

## Requirements

* Windows
* Python x64 3.7 - 3.11
* (Windows) [VC++ redistributables](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads>) (already installed if you have MIKE)

## Installation

```
$ pip install mikeio1d
```

## Getting started

```python
>>>  from mikeio1d import Res1D
>>>  res = Res1D('simple.res1d')
>>>  df = res.read()
```

Read more in the [getting started guide](getting-started).


Where can I get help?
---------------------

* New ideas and feature requests - [GitHub Discussions](https://github.com/DHI/mikeio1d/discussions)
* Bugs - [GitHub Issues](https://github.com/DHI/mikeio1d/issues)

```{eval-rst}
.. toctree::
   :maxdepth: 2
   :caption: Contents:
   :hidden:

   getting-started
   design
   res1d
```