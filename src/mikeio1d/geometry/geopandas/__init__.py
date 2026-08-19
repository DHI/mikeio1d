"""Package for converting ResultLocations to GeoPandas objects."""

from mikeio1d.various import try_import_geopandas, try_import_shapely

# check if geopandas and shapely are available
try_import_geopandas()
try_import_shapely()

from .geopandas_catchments_converter import GeoPandasCatchmentsConverter
from .geopandas_nodes_converter import GeoPandasNodesConverter
from .geopandas_reaches_converter import GeoPandasReachesConverter
from .geopandas_reaches_converter_segmented import GeoPandasReachesConverterSegmented

__all__ = [
    "GeoPandasCatchmentsConverter",
    "GeoPandasNodesConverter",
    "GeoPandasReachesConverter",
    "GeoPandasReachesConverterSegmented",
]
