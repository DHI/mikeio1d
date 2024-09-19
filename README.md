![logo](https://raw.githubusercontent.com/DHI/mikeio1d/main/images/logo/MIKE-IO-1D-Logo-Pos-RGB-nomargin.png)
# MIKE IO 1D: Read MIKE 1D in python

Read res1d and xns11 files.

For other MIKE files (Dfs0, Dfs1, Dfs2, Dfsu,...) use the related package [MIKE IO](https://github.com/DHI/mikeio)

## Requirements
* Windows operating system (Support for Linux is experimental)
* Python x64 3.9, 3.10, 3.11 or 3.12 
* [VC++ redistributables](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads) (already installed if you have MIKE)

## Installation

From PyPI: 

`pip install mikeio1d`

Or development version:

`pip install https://github.com/DHI/mikeio1d/archive/main.zip`


For MIKE IO 1D to work .NET runtime environment (version 3.1 and above) is needed. On Linux operating systems this is not available per default. For example, on Ubuntu distribution to get .NET 7.0 runtime call:

`sudo apt install dotnet-runtime-7.0`

## Where can I get help?

* New ideas and feature requests - [GitHub Discussions](http://github.com/DHI/mikeio1d/discussions) 
* Bugs - [GitHub Issues](http://github.com/DHI/mikeio1d/issues) 
* General help, FAQ - [Stackoverflow with the tag `mikeio`](https://stackoverflow.com/questions/tagged/mikeio1d)


## Examples

### Read Res1D file Return Pandas DataFrame
```python
>>>  from mikeio1d.res1d import Res1D, QueryDataReach
>>>  df = Res1D(filename).read()

>>>  query = QueryDataReach("WaterLevel", "104l1", 34.4131)
>>>  df = res1d.read(query)
```
For more Res1D examples see this [notebook](https://nbviewer.jupyter.org/github/DHI/mikeio1d/blob/main/notebooks/Res1D.ipynb)

### Read Xns11 file and plot a cross section
```python
>>>  from mikeio1d import Xns11

# Plot section with location id 'basin_right', chainage '238.800', and topo id '1'.
>>>  xns = Xns11("mikep_cs_demo.xns11")
>>>  xns.xsections.['basin_right', '238.800', '1'].plot()
```
![Geometry](https://raw.githubusercontent.com/DHI/mikeio1d/main/images/xns11_geometry.png)
