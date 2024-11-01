"""Package for converting ResultLocations to GeoPandas objects."""

from mikeio1d.various import try_import_geopandas
from mikeio1d.various import try_import_shapely

# check if geopandas and shapely are available
try_import_geopandas()
try_import_shapely()

from .geopandas_reaches_converter import GeoPandasReachesConverter  # noqa: E402
from .geopandas_reaches_converter_segmented import GeoPandasReachesConverterSegmented  # noqa: E402
from .geopandas_nodes_converter import GeoPandasNodesConverter  # noqa: E402
from .geopandas_catchments_converter import GeoPandasCatchmentsConverter  # noqa: E402

__all__ = [
    "GeoPandasReachesConverter",
    "GeoPandasReachesConverterSegmented",
    "GeoPandasNodesConverter",
    "GeoPandasCatchmentsConverter",
]
