"""Package for fluent access to MIKE 1D results."""

from .result_catchment import ResultCatchment
from .result_catchments import ResultCatchments
from .result_gridpoint import ResultGridPoint
from .result_location import ResultLocation
from .result_locations import ResultLocations
from .result_network import ResultNetwork
from .result_node import ResultNode
from .result_nodes import ResultNodes
from .result_quantity import ResultQuantity
from .result_quantity_collection import ResultQuantityCollection
from .result_global_data import ResultGlobalData
from .result_global_datas import ResultGlobalDatas
from .result_reach import ResultReach
from .result_reaches import ResultReaches
from .result_structure import ResultStructure
from .result_structures import ResultStructures
from .various import make_proper_variable_name

__all__ = [
    "ResultCatchment",
    "ResultCatchments",
    "ResultNode",
    "ResultNodes",
    "ResultReach",
    "ResultReaches",
    "ResultStructure",
    "ResultStructures",
    "ResultGridPoint",
    "ResultGlobalData",
    "ResultGlobalDatas",
    "ResultQuantity",
    "ResultQuantityCollection",
]
