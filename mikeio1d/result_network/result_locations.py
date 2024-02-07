from __future__ import annotations

from typing import TYPE_CHECKING

from typing import Dict

if TYPE_CHECKING:
    from typing import List
    from typing import Optional

    import pandas as pd

    from ..res1d import Res1D
    from .result_location import ResultLocation
    from .result_quantity import ResultQuantity
    from ..result_reader_writer.result_reader import ColumnMode

from .result_location import ResultLocation

from ..dotnet import pythonnet_implementation as impl
from .result_quantity_collection import ResultQuantityCollection
from .various import make_proper_variable_name
from .various import build_html_repr_from_sections


class ResultLocations(Dict[str, ResultLocation]):
    """
    A base class for a network locations (nodes, reaches)
    or a catchments wrapper class.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the result location belongs to.

    Attributes
    ----------
    data : ResultData
        MIKE 1D ResultData object.
    data_items : IDataItems.
        MIKE 1D IDataItems object.
    quantity_label : str
        A label, which is appended if the quantity id starts
        with a number. The value used is quantity_label = 'q_'
    result_quantity_map : dict
        Dictionary from quantity id to a list of ResultQuantity objects.
    """

    def __init__(self, res1d: Res1D):
        self.res1d = res1d
        self.quantity_label = "q_"
        self.data = res1d.data
        self.data_items = res1d.data.DataItems
        self.result_quantity_map: Dict[str : List[ResultQuantity]] = {}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    def _repr_html_(self) -> str:
        total_names = len(self)
        total_quantities = len(self.quantities)
        repr = build_html_repr_from_sections(
            self.__repr__(),
            [
                (f"Names ({total_names})", self.names),
                (f"Quantities ({total_quantities})", list(self.quantities.keys())),
            ],
        )
        return repr

    @property
    def quantities(self) -> Dict[str, ResultQuantityCollection]:
        """A list of available quantities."""
        return {k: getattr(self, k) for k in self.result_quantity_map}

    @property
    def names(self) -> List[str]:
        """A list of location names (e.g. MUIDs)."""
        return list(self.keys())

    @property
    def locations(self) -> List[ResultLocation]:
        """A list of location objects (e.g. <ResultNode>)."""
        return list(self.values())

    def read(self, column_mode: Optional[str | ColumnMode] = None) -> pd.DataFrame:
        """
        Read the time series data for all quantities at these locations into a DataFrame.

        Parameters
        ----------
        column_mode : str | ColumnMode (optional)
            Specifies the type of column index of returned DataFrame.
            'all' - column MultiIndex with levels matching TimeSeriesId objects.
            'compact' - same as 'all', but removes levels with default values.
            'timeseries' - column index of TimeSeriesId objects
        """
        result_quantities = [q for qlist in self.result_quantity_map.values() for q in qlist]
        timesries_ids = [q.timeseries_id for q in result_quantities]
        df = self.res1d.result_reader.read(timesries_ids, column_mode=column_mode)
        return df

    def set_quantity_collections(self):
        """Sets all quantity collection attributes."""
        for quantity_id in self.result_quantity_map:
            result_quantities = self.result_quantity_map[quantity_id]
            result_quantity_collection = ResultQuantityCollection(result_quantities, self.res1d)
            result_quantity_attribute_string = make_proper_variable_name(
                quantity_id, self.quantity_label
            )
            setattr(self, result_quantity_attribute_string, result_quantity_collection)

    def set_res1d_object_to_dict(self, dict_key, obj):
        """
        Create a dict entry from a key name to an object
        or a list of objects.
        """
        obj = impl(obj)
        if dict_key in self:
            value = self[dict_key]
            if not isinstance(value, list):
                self[dict_key] = [value]

            self[dict_key].append(obj)
        else:
            self[dict_key] = obj
