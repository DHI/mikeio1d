![logo](https://raw.githubusercontent.com/DHI/mikeio1d/main/images/logo/MIKE-IO-1D-Logo-Pos-RGB-nomargin.png)
# MIKE IO 1D: Read MIKE 1D in python

Read res1d and xns11 files.

For other MIKE files (Dfs0, Dfs1, Dfs2, Dfsu,...) use the related package [MIKE IO](https://github.com/DHI/mikeio)

## Requirements
* Windows operating system
* Python x64 3.6, 3.7 or 3.8 
* [VC++ redistributables](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads) (already installed if you have MIKE)

## Installation

From PyPI: 

`pip install mikeio1d`

Or development version:

`pip install https://github.com/DHI/mikeio1d/archive/main.zip`


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

### Read Xns11 file Return Pandas DataFrame
```python
>>>  import matplotlib.pyplot as plt
>>>  from mikeio1d import xns11
>>>  # Query the geometry of chainage 58.68 of topoid1 at reach1
>>>  q1 = xns11.QueryData('topoid1', 'reach1', 58.68)
>>>  # Query the geometry of all chainages of topoid1 at reach2
>>>  q2 = xns11.QueryData('topoid1', 'reach2')
>>>  # Query the geometry of all chainages of topoid2
>>>  q3 = xns11.QueryData('topoid2')
>>>  # Combine the queries in a list
>>>  queries = [q1, q2, q3]
>>>  # The returned geometry object is a pandas DataFrame
>>>  geometry = xns11.read('xsections.xns11', queries)
>>>  # Plot geometry of chainage 58.68 of topoid1 at reach1
>>>  plt.plot(geometry['x topoid1 reach1 58.68'],geometry['z topoid1 reach1 58.68'])
>>>  plt.xlabel('Horizontal [meter]')
>>>  plt.ylabel('Elevation [meter]')
```
![Geometry](https://raw.githubusercontent.com/DHI/mikeio1d/main/images/xns11_geometry.png)
