from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict
    from typing import Callable
    from geopandas import GeoDataFrame

from ..dotnet import pythonnet_implementation as impl
from .result_locations import ResultLocations
from .result_catchment import ResultCatchment
from .various import make_proper_variable_name
from ..various import try_import_geopandas
from ..various import pyproj_crs_from_projection_string
from ..pandas_extension import ResultFrameAggregator


class ResultCatchments(ResultLocations):
    """
    Class for wrapping ResultData catchments.

    By itself it is also a dict, which contains
    mapping between catchment ID and IRes1DCatchment object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the catchments belong to.

    Attributes
    ----------
    catchment_label : str
        A label, which is appended if the catchment name starts
        with a number. The value used is catchment_label = 'c_'
    """

    def __init__(self, res1d):
        ResultLocations.__init__(self, res1d)
        self.catchment_label = "c_"

        res1d.result_network.catchments = self
        self.set_catchments()
        self.set_quantity_collections()

        self._catchment_ids = None
        self._geometries = None

    def set_catchments(self):
        """
        Set attributes to the current ResultCatchments object based
        on the catchment ID.
        """
        for catchment in self.data.Catchments:
            catchment = impl(catchment)
            result_catchment = ResultCatchment(catchment, self.res1d)
            self.set_res1d_catchment_to_dict(result_catchment)
            result_catchment_attribute_string = make_proper_variable_name(
                result_catchment.id, self.catchment_label
            )
            setattr(self, result_catchment_attribute_string, result_catchment)

    def set_res1d_catchment_to_dict(self, catchment):
        """
        Create a dict entry from catchment ID to ResultCatchment object.
        """
        self[catchment.id] = catchment

    def to_geopandas(
        self,
        agg: str | Callable = None,
        agg_kwargs: Dict[str : str | Callable] = {},
    ) -> GeoDataFrame:
        """
        Convert catchments to a geopandas.GeoDataFrame object.

        By default, the result quantities are aggregated unless agg is specified.

        Parameters
        ----------
        agg : str or callable, default None
            Aggregation strategy. How to aggregate the quantities in time and space.
        agg_kwargs : dict, default {}
            Aggregation strategy for specific levels (e.g. {time='min', chainage='first'}).

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame object with catchments as Polygon geometries.
        """
        gpd = try_import_geopandas()
        if not self._catchment_ids or not self._geometries:
            values = self.values()
            self._catchment_ids = [catchment.id for catchment in values]
            self._geometries = [catchment.geometry.to_shapely() for catchment in values]

        ids = self._catchment_ids
        geometries = self._geometries
        data = {"name": ids, "geometry": geometries}
        crs = pyproj_crs_from_projection_string(self.res1d.projection_string)
        gdf = gpd.GeoDataFrame(data=data, crs=crs)

        if agg is None:
            return gdf

        rfa = ResultFrameAggregator(agg, **agg_kwargs)

        df_quantities = self.read(column_mode="compact")
        df_quantities = rfa.aggregate(df_quantities)

        gdf = gdf.merge(df_quantities, left_on="name", right_index=True)

        return gdf
