=(network_structure)
# Network structure

A fundamental concept in MIKE IO 1D is the network structure. Every single result is attached to a part of the network. Knowing this structure will help you navigate to results you're interested in. This sections provides a brief introduction to this structure. For additional information, refer to the [MIKE 1D API](https://docs.mikepoweredbydhi.com/engine_libraries/mike1d/mike1d_api/#dhimike1dnetworkdataaccess).

## Overview
MIKE result networks consist of the following four geometric types:
* Nodes
* Reaches (consisting of grid points)
* Catchments
* Global data

```{figure} ./_static/NetworkExample.png
:width: 50%

Figure 1 - A network consisting of nodes and reaches.
```

```{figure} ./_static/NetworkCatchments.svg
:width: 50%

Figure 2 - A network with catchments associated with nodes.
```

## Reaches
A reach has many synonyms within different domain applications. In sewer models it is often called a link or pipe, in river models a branch, stream, canal or channel, and in graph and network theory it is called a link or an edge. A reach contains several 'grid points' along its path.

## Grid Points
Grid points are the computational points along a reach. A flow model has different types of grid points:
* H grid point: contains water level and an associated cross section
* Q grid point: contains discharge or flow velocity.
* Structure grid point: calculates discharge over a structure depending on the water levels on each side of the structure.

## Nodes
Nodes are attached to one or more reaches. Nodes can be one of several types, including: manholes, basins, outlets, and junction nodes. They may or may not have a volume.

## Catchments
Catchments are geographical areas associated with a result (e.g. hydrologic models consist of several catchments). They are connected to a point on the network (e.g. node or grid point).
