![logo](https://raw.githubusercontent.com/DHI/mikeio1d/main/images/logo/MIKE-IO-1D-Logo-Pos-RGB-nomargin.png)
# MIKE IO 1D: Read MIKE 1D in python
 ![Python version](https://img.shields.io/pypi/pyversions/mikeio1d.svg)
 [![Full test](https://github.com/DHI/mikeio1d/actions/workflows/full_test.yml/badge.svg)](https://github.com/DHI/mikeio1d/actions/workflows/full_test.yml)
[![PyPI version](https://badge.fury.io/py/mikeio1d.svg)](https://badge.fury.io/py/mikeio1d)
![OS](https://img.shields.io/badge/OS-Windows%20%7C%20Linux-blue)
![Downloads](https://img.shields.io/pypi/dm/mikeio1d)

Read, manipulate, and analyze res1d, res, resx, out, and xns11 files.

For other MIKE files (Dfs0, Dfs1, Dfs2, Dfsu,...) use the related package [MIKE IO](https://github.com/DHI/mikeio)

Most users of MIKE IO 1D will also find [MIKE+Py](https://github.com/DHI/mikepluspy) of interest.

## Requirements
* Windows, Linux (experimental)
* Python x64 3.9 - 3.13
* (Windows) [VC++ redistributables](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads) (already installed if you have MIKE)
* (Linux) [.NET Runtime](https://learn.microsoft.com/en-us/dotnet/core/install/linux) (not installed by default)

## Installation

From PyPI: 

`pip install mikeio1d`

Linux users will need to install .NET runtime. For Ubuntu, you can install .NET runtime as follows:

`sudo apt install dotnet-runtime-8.0`

Or development version:

`pip install https://github.com/DHI/mikeio1d/archive/main.zip`

If you're on the development branch, you need .NET SDK. Ubuntu users can install these dependencies as follows:

`sudo apt install dotnet-sdk-8.0`

## Documentation

Check out the [official documentation for MIKE IO 1D](https://dhi.github.io/mikeio1d/).

## Getting started

### Read network results into a DataFrame
```python
>>>  from mikeio1d import Res1D
>>>  res = Res1D('my_results.res1d')
>>>  df = res.read()

>>>  df_reach = res.reaches['my_reach'].Discharge.read()
>>>  df_node  = res.nodes['my_node'].WaterLevel.read()
```

### Read Xns11 file and plot a cross section
```python
>>>  from mikeio1d import Xns11

# Plot section with location id 'basin_right', chainage '238.800', and topo id '1'.
>>>  xns = Xns11("mikep_cs_demo.xns11")
>>>  xns.xsections['basin_right', '238.800', '1'].plot()
```
![Geometry](https://raw.githubusercontent.com/DHI/mikeio1d/main/images/xns11_geometry.png)

Continue learning with [additional examples](https://dhi.github.io/mikeio1d/examples/res1d_basic.html).

## Where can I get help?

* Reference - [Documentation](https://dhi.github.io/mikeio1d/)
* New ideas and feature requests - [GitHub Discussions](http://github.com/DHI/mikeio1d/discussions) 
* Bugs - [GitHub Issues](http://github.com/DHI/mikeio1d/issues) 
