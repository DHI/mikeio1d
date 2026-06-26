"""Module for ResultReaches class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from typing import Callable
    from typing import List
    from typing import Dict
    from geopandas import GeoDataFrame

    from ..res1d import Res1D

    from DHI.Mike1D.ResultDataAccess import IRes1DReach

from ..dotnet import pythonnet_implementation as impl
from ..pandas_extension import ResultFrameAggregator
from ..quantities import TimeSeriesIdGroup

from .result_locations import ResultLocations
from .result_locations import ResultLocationsCreator
from .result_reach import ResultReach
from .various import make_proper_variable_name


class ResultReaches(ResultLocations):
    """Class for wrapping ResultData reaches.

    By itself it is also a dict, which contains
    mapping between reach name and IRes1DReach object
    or a list of IRes1DReach objects.


    Parameters
    ----------
    res1d : Res1D
        Res1D object the reaches belong to.

    """

    def __init__(self, res1d: Res1D):
        ResultLocations.__init__(self)

        res1d.network.reaches = self
        self._group = TimeSeriesIdGroup.REACH

        self._creator = ResultReachesCreator(self, res1d)
        self._creator.create()

    def to_geopandas(
        self,
        agg: str | Callable = None,
        agg_kwargs: Dict[str : str | Callable] = {},
        segmented: bool = True,
        include_derived: bool = False,
    ) -> GeoDataFrame:
        """Convert reaches to a geopandas.GeoDataFrame object.

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
        segmented : bool, (default=True)
            True - one LineString per IRes1DReach object.
            False - one LineString per reach name.
        include_derived : bool, default False
            Include derived quantities.

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame object with reaches as LineString geometries.

        Examples
        --------
        # Convert reaches to a GeoDataFrame (without quantities)
        >>> gdf = res1d.reaches.to_geopandas()

        # Convert reaches to a GeoDataFrame with aggregated quantities
        >>> gdf = res1d.reaches.to_geopandas(agg='mean')

        """
        from mikeio1d.geometry.geopandas import GeoPandasReachesConverter
        from mikeio1d.geometry.geopandas import GeoPandasReachesConverterSegmented

        if segmented:
            gpd_converter = GeoPandasReachesConverterSegmented()
        else:
            gpd_converter = GeoPandasReachesConverter()

        gdf = gpd_converter.to_geopandas(self)

        if agg is None:
            return gdf

        rfa = ResultFrameAggregator(agg, **agg_kwargs)

        df_quantities = self.read(column_mode="compact", include_derived=include_derived)
        df_quantities = rfa.aggregate(df_quantities)

        if segmented:
            gdf = gdf.merge(df_quantities, left_on=["name", "tag"], right_index=True)
        else:
            df_quantities = df_quantities.groupby("name").agg(rfa.get_agg_function("time"))
            gdf = gdf.merge(df_quantities, left_on="name", right_index=True)

        return gdf


class ResultReachesCreator(ResultLocationsCreator):
    """A helper class for creating ResultReaches.

    Parameters
    ----------
    result_locations : ResultReaches
        Instance of ResultReaches, which the ResultReachesCreator deals with.
    res1d : Res1D
        Res1D object the reaches belong to.

    Attributes
    ----------
    reach_label : str
        A label, which is appended if the reach name starts
        with a number. The value used is reach_label = 'r_'
    result_reach_map : dict
        Dictionary from reach name to a list of ResultReach objects.
        This is needed, because the reach name is not necessarily unique and
        several reaches could have the same name.

    """

    def __init__(self, result_locations: ResultReaches, res1d: Res1D):
        ResultLocationsCreator.__init__(self, result_locations, res1d)
        self.reach_label = "r_"
        self.result_reach_map: Dict[str : List[ResultReach]] = {}

    def create(self):
        """Perform ResultReaches creation steps."""
        self.set_reaches()
        self.set_quantity_collections()

    def set_reaches(self):
        """Set attributes to the current ResultReaches object based on the reach name."""
        for reach in self.data.Reaches:
            # TODO: Figure out if we should we have res1d.reader dependency here?
            if not self.res1d.reader.is_data_set_included(reach):
                continue

            reach = impl(reach)
            result_reach = self.get_or_create_result_reach(reach)
            result_reach_attribute_string = make_proper_variable_name(reach.Name, self.reach_label)
            setattr(self.result_locations, result_reach_attribute_string, result_reach)

    def set_quantity_collections(self):
        """Set quantity collections to the current ResultReaches object."""
        ResultLocationsCreator.set_quantity_collections(self)
        for reach_name in self.result_locations:
            result_reach = self.result_locations[reach_name]
            ResultLocationsCreator.set_quantity_collections(result_reach._creator, result_reach)

    def get_or_create_result_reach(self, reach: IRes1DReach) -> ResultReach:
        """Create or get already existing ResultReach object.

        There potentially could be just a single ResultReach object,
        for many IRes1DReach object, which have the same name.

        Also update self's dict entry from reach name
        to a ResultReach object.
        """
        if reach.Name in self.result_locations:
            result_reach = self.result_locations[reach.Name]
            result_reach._creator.add_res1d_reach(reach)
            return result_reach

        result_reach = ResultReach([reach], self.res1d)
        self.result_locations[reach.Name] = result_reach
        return result_reach
