"""ResultCatchments class."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Dict
    from typing import Callable
    from geopandas import GeoDataFrame

    from ..res1d import Res1D

    from DHI.Mike1D.ResultDataAccess import Res1DCatchment

from ..dotnet import pythonnet_implementation as impl
from ..pandas_extension import ResultFrameAggregator
from ..quantities import TimeSeriesIdGroup

from .result_locations import ResultLocations
from .result_locations import ResultLocationsCreator
from .result_catchment import ResultCatchment
from .various import make_proper_variable_name


class ResultCatchments(ResultLocations):
    """Class for wrapping ResultData catchments.

    By itself it is also a dict, which contains
    mapping between catchment ID and IRes1DCatchment object.

    Parameters
    ----------
    res1d : Res1D
        Res1D object the catchments belong to.

    """

    def __init__(self, res1d: Res1D):
        ResultLocations.__init__(self)

        res1d.network.catchments = self
        self._group = TimeSeriesIdGroup.CATCHMENT

        self._creator = ResultCatchmentsCreator(self, res1d)
        self._creator.create()

    def to_geopandas(
        self,
        agg: str | Callable = None,
        agg_kwargs: Dict[str : str | Callable] = {},
    ) -> GeoDataFrame:
        """Convert catchments to a geopandas.GeoDataFrame object.

        By default, quantities are not included. To include quantities, use the `agg` and `agg_kwargs` parameters.

        Parameters
        ----------
        agg : str or callable, default None
            Defines how to aggregate the quantities in time and space.
            Accepts any str or callable that is accepted by pandas.DataFrame.agg.

        Examples
        --------
            - 'mean'  : mean value of all quantities
            - 'max'   : maximum value of all quantities
            -  np.max : maximum value of all quantities

        agg_kwargs : dict, default {}
            Aggregation function for specific column levels (e.g. {time='min', chainage='first'}).

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame object with catchments as Polygon geometries.

        """
        from ..geometry.geopandas import GeoPandasCatchmentsConverter

        gpd_converter = GeoPandasCatchmentsConverter()
        gdf = gpd_converter.to_geopandas(self)

        if agg is None:
            return gdf

        rfa = ResultFrameAggregator(agg, **agg_kwargs)

        df_quantities = self.read(column_mode="compact")
        df_quantities = rfa.aggregate(df_quantities)

        gdf = gdf.merge(df_quantities, left_on="name", right_index=True)

        return gdf


class ResultCatchmentsCreator(ResultLocationsCreator):
    """A helper class for creating ResultCatchments.

    Parameters
    ----------
    result_locations : ResultCatchments
        Instance of ResultCatchments, which the ResultCatchmentsCreator deals with.
    res1d : Res1D
        Res1D object the catchments belong to.

    Attributes
    ----------
    catchment_label : str
        A label, which is appended if the catchment name starts
        with a number. The value used is catchment_label = 'c_'

    """

    def __init__(self, result_locations: ResultCatchments, res1d: Res1D):
        ResultLocationsCreator.__init__(self, result_locations, res1d)
        self.catchment_label = "c_"

    def create(self):
        """Perform ResultCatchments creation steps."""
        self.set_catchments()
        self.set_quantity_collections()

    def set_catchments(self):
        """Set attributes to the current ResultCatchments object based on the catchment ID."""
        for catchment in self.data.Catchments:
            catchment: Res1DCatchment = impl(catchment)
            # TODO: Figure out if we should we have res1d.reader dependency here?
            if not self.res1d.reader.is_data_set_included(catchment):
                continue

            result_catchment = ResultCatchment(catchment, self.res1d)
            self.set_res1d_catchment_to_dict(result_catchment)
            result_catchment_attribute_string = make_proper_variable_name(
                result_catchment.id, self.catchment_label
            )
            setattr(self.result_locations, result_catchment_attribute_string, result_catchment)

    def set_res1d_catchment_to_dict(self, result_catchment: ResultCatchment):
        """Create a dict entry from catchment ID to ResultCatchment object."""
        self.result_locations[result_catchment.id] = result_catchment
