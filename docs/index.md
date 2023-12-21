![](../images/logo/MIKE-IO-1D-Logo-Pos-RGB-nomargin.png)

# Welcome to MIKE IO 1D's documentation!
 ![Python version](https://img.shields.io/pypi/pyversions/mikeio1d.svg)
[![PyPI version](https://badge.fury.io/py/mikeio1d.svg)](https://badge.fury.io/py/mikeio1d)

MIKE IO 1D is a python library for reading and modifying network result files (e.g. .res1d). Its target audience is scientists, engineers, and modellers working with MIKE 1D network results.

For other MIKE files (dfs0, dfs1, dfs2, dfsu, and mesh files) use the related package [MIKE IO](https://github.com/DHI/mikeio)

```{caution} MIKE IO 1D is under development and could be subject to changes.
```

## Requirements

* Windows, Linux (experimental)
* Python x64 3.8 - 3.12
* (Windows) [VC++ redistributables](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads>) (already installed if you have MIKE)
* (Linux) [.NET Runtime](https://learn.microsoft.com/en-us/dotnet/core/install/linux) (not installed by default)

## Installation

```bash
$ pip install mikeio1d
```

Linux users will need to install .NET runtime. If you're on the development branch, you need .NET SDK. Ubuntu users can install these dependencies as follows:

```bash
$ sudo apt install dotnet-runtime-7.0
```

```bash
$ sudo apt install dotnet-sdk-7.0
```



## Getting started

```python
>>> from mikeio1d import Res1D
>>> res = Res1D('simple.res1d')
>>> df = res.read()
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

   design
   getting-started
   network
   res1d
   xns11
```
