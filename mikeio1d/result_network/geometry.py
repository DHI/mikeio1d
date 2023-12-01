import shapely


def geometry_from_node(dotnet_node) -> shapely.Point:
    """
    Create a shapely Point from an IRes1DNode object.

    Parameters
    ----------
    dotnet_node : IRes1DNode

    Returns
    -------
    shapely.Point
    """
    xcoord = dotnet_node.XCoordinate
    ycoord = dotnet_node.YCoordinate
    geometry = shapely.Point(xcoord, ycoord)
    return geometry


def geometry_from_reach(dotnet_reach) -> shapely.LineString:
    """
    Create a shapely LineString from an IRes1DReach object.

    Parameters
    ----------
    dotnet_reach : IRes1DReach

    Returns
    -------
    shapely.LineString
    """
    digipoints = dotnet_reach.DigiPoints
    xy = [(dp.X, dp.Y) for dp in digipoints]
    geometry = shapely.LineString(xy)
    return geometry


def geometry_from_reaches(dotnet_reaches) -> shapely.LineString:
    """
    Create a shapely LineString from an interable of IRes1DReach objects.

    Useful for joining multiple IRes1DReach objects that share the same name.

    Parameters
    ----------
    dotnet_reach : iterable of IRes1DReach

    Returns
    -------
    shapely.LineString
    """
    linestrings = [geometry_from_reach(reach) for reach in dotnet_reaches]
    geometry = shapely.MultiLineString(linestrings)
    geometry = shapely.line_merge(geometry)
    return geometry


def geometry_from_catchment(dotnet_catchment) -> shapely.Polygon:
    """Get a shapely Polygon from a catchment."""
    shape = dotnet_catchment.Shape[0]  # there will always be one element
    coords = []
    for i in range(shape.VertexCount()):
        vertex = shape.GetVertex(i)
        coords.append((vertex.X, vertex.Y))
    geometry = shapely.Polygon(coords)
    return geometry
