"""Module for ResultNetwork class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import List
    from typing import Dict
    from geopandas import GeoDataFrame

    from ..res1d import Res1D

    from DHI.Mike1D.ResultDataAccess import ResultData
    from DHI.Mike1D.ResultDataAccess import IDataItem

import pandas as pd

from ..various import try_import_geopandas

from .result_nodes import ResultNodes
from .result_reaches import ResultReaches
from .result_catchments import ResultCatchments
from .result_global_datas import ResultGlobalDatas
from .result_structures import ResultStructures
from .result_quantity import ResultQuantity
from ..quantities import TimeSeriesId
from ..quantities import DerivedQuantity


class ResultNetwork:
    """Class for storing ResultData network wrapper.

    This class is mainly used to provide for network
    location attributes, which can then be accessed
    in an IDE using auto-completion.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the network belongs to.

    Attributes
    ----------
    data : ResultData
        MIKE 1D ResultData object.
    data_items : IDataItems.
        MIKE 1D IDataItems object.
    queue: list
        A list of TimeSeriesId objects to be used when calling res1D.read().
    nodes : ResultNodes object
        Is is a wrapper class object for all ResultData nodes.
    reaches : ResultReaches object
        Is a wrapper class object for all ResultData reaches.
    catchments : ResultCatchments object
        Is a wrapper class object for all ResultData catchments.
    global_data : ResultGlobalDatas object
        Is a wrapper class object for all ResultData global data items.
    result_quantity_map : dict
        Dictionary from TimeSeriesId to a corresponding ResultQuantity object.
        The keys of this dictionary represent all possible TimeSeriesId
        objects that can be queried from the ResultNetwork.

    Examples
    --------
    An example of adding a query for some location using ResultNetwork
    for nodes with ID 'node1', 'node2' and reaches with ID 'reach1', 'reach2'
    and chainage equal 0, for WaterLevel quantity:
    ```python
    >>> res1d = Res1D('MyRes1D.res1d')
    >>> resnet = ResultNetwork(res1d)
    >>> resnet.nodes.node1.WaterLevel.add()
    >>> resnet.nodes.node2.WaterLevel.add()
    >>> resnet.reaches.reach1.m_0_0.WaterLevel.add()
    >>> resnet.reaches.reach2.m_0_0.WaterLevel.add()
    ```

    """

    def __init__(self, res1d: Res1D):
        self.res1d = res1d
        self.data: ResultData = res1d.result_data
        self.data_items: List[IDataItem] = res1d.result_data.DataItems

        self.queue: List[TimeSeriesId] = []

        self.result_quantity_map: Dict[TimeSeriesId, ResultQuantity] = {}

        self.res1d.network = self
        self._set_result_locations()

    def _add_result_quantity_to_map(self, result_quantity: ResultQuantity) -> TimeSeriesId:
        """Add a ResultQuantity to map of all possible ResultQuantities.

        Parameters
        ----------
        result_quantity : ResultQuantity
            ResultQuantity object to be added to the result_quantity_map.

        Returns
        -------
        TimeSeriesId
            The TimeSeriesId key of the added ResultQuantity

        """
        tsid = TimeSeriesId.from_result_quantity(result_quantity)
        while tsid in self.result_quantity_map:
            if self.result_quantity_map[tsid] == result_quantity:
                break
            tsid = tsid.next_duplicate()
        result_quantity._timeseries_id = tsid
        self.result_quantity_map[tsid] = result_quantity

        return tsid

    def _set_result_locations(self):
        """Assign nodes, reaches, catchments, global_data properties."""
        res1d = self.res1d
        self.nodes = ResultNodes(res1d)
        self.reaches = ResultReaches(res1d)
        self.catchments = ResultCatchments(res1d)
        self.structures = ResultStructures(res1d)
        self.global_data = ResultGlobalDatas(res1d)

    def add_timeseries_id(self, timeseries_id: TimeSeriesId):
        """Add a TimeSeriesId to the queue list, which can be used when calling res1D.read()."""
        if timeseries_id not in self.queue:
            self.queue.append(timeseries_id)

    def add_derived_quantity(self, derived_quantity: ResultQuantity):
        """Add a derived quantity to the result network.

        Parameters
        ----------
        derived_quantity : Type[ResultQuantity]
            Derived quantity to be added to the result network.

        """
        self.nodes._creator.add_derived_quantity(derived_quantity)
        self.reaches._creator.add_derived_quantity(derived_quantity)
        self.catchments._creator.add_derived_quantity(derived_quantity)
        self.structures._creator.add_derived_quantity(derived_quantity)

    def remove_derived_quantity(self, derived_quantity: ResultQuantity | str):
        """Remove a derived quantity from the result network.

        Parameters
        ----------
        derived_quantity : ResultQuantity or str
            Derived quantity to be removed from the result network. Either a ResultQuantity object or its name.

        """
        self.nodes._creator.remove_derived_quantity(derived_quantity)
        self.reaches._creator.remove_derived_quantity(derived_quantity)
        self.catchments._creator.remove_derived_quantity(derived_quantity)
        self.structures._creator.remove_derived_quantity(derived_quantity)

    def to_geopandas(self) -> GeoDataFrame:
        """Convert ResultNetwork to a GeoDataFrame. Require geopandas to be installed."""
        gpd = try_import_geopandas()  # noqa: F841
        gdf_nodes = self.nodes.to_geopandas()
        gdf_reaches = self.reaches.to_geopandas()
        gdf_catchments = self.catchments.to_geopandas()

        gdfs = [gdf_nodes, gdf_reaches, gdf_catchments]
        gdfs = [gdf for gdf in gdfs if not gdf.empty]

        gdf = pd.concat(gdfs, ignore_index=True)
        return gdf
