from mikeio1d.various import try_import_geopandas
from mikeio1d.various import try_import_shapely

# check if geopandas and shapely are available
try_import_geopandas()
try_import_shapely()

from .geopandas_reaches_converter import GeopandasReachesConverter  # noqa: E402
from .geopandas_reaches_converter_segmented import GeopandasReachesConverterSegmented  # noqa: E402
from .geopandas_nodes_converter import GeoPandasNodesConverter  # noqa: E402
from .geopandas_catchments_converter import GeoPandasCatchmentsConverter  # noqa: E402

__all__ = [
    "GeopandasReachesConverter",
    "GeopandasReachesConverterSegmented",
    "GeoPandasNodesConverter",
    "GeoPandasCatchmentsConverter",
]
