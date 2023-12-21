from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geopandas import GeoDataFrame

from .result_locations import ResultLocations
from .result_reach import ResultReach
from .various import make_proper_variable_name
from ..various import try_import_geopandas
from ..various import pyproj_crs_from_projection_string
from ..dotnet import pythonnet_implementation as impl


class ResultReaches(ResultLocations):
    """
    Class for wrapping ResultData reaches.

    By itself it is also a dict, which contains
    mapping between reach name and IRes1DReach object
    or a list of IRes1DReach objects.


    Parameters
    ----------
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

    def __init__(self, res1d):
        ResultLocations.__init__(self, res1d)
        self.reach_label = "r_"
        self.result_reach_map = {}

        res1d.result_network.reaches = self
        self.set_reaches()
        self.set_quantity_collections()

    def set_reaches(self):
        """
        Set attributes to the current ResultReaches object based
        on the reach name.
        """
        for reach in self.data.Reaches:
            reach = impl(reach)
            result_reach = self.get_or_create_result_reach(reach)
            result_reach_attribute_string = make_proper_variable_name(reach.Name, self.reach_label)
            setattr(self, result_reach_attribute_string, result_reach)

    def set_quantity_collections(self):
        ResultLocations.set_quantity_collections(self)
        for reach_name in self:
            result_reach = self[reach_name]
            ResultLocations.set_quantity_collections(result_reach)

    def get_or_create_result_reach(self, reach):
        """
        Create or get already existing ResultReach object.
        There potentially could be just a single ResultReach object,
        for many IRes1DReach object, which have the same name.

        Also update self's dict entry from reach name
        to a ResultReach object.
        """
        if reach.Name in self:
            result_reach = self[reach.Name]
            result_reach.add_res1d_reach(reach)
            return result_reach

        result_reach = ResultReach([reach], self.res1d)
        self[reach.Name] = result_reach
        return result_reach

    def to_geopandas(self) -> GeoDataFrame:
        """
        Convert reaches to a geopandas.GeoDataFrame object.

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            A GeoDataFrame object with reaches as LineString geometries.
        """
        gpd = try_import_geopandas()
        ids = [reach.name for reach in self.values()]
        geometries = [reach.geometry.to_shapely() for reach in self.values()]
        data = {"id": ids, "geometry": geometries}
        crs = pyproj_crs_from_projection_string(self.res1d.projection_string)
        gdf = gpd.GeoDataFrame(data=data, crs=crs)
        return gdf
