from warnings import warn

from ..query import QueryDataCatchment
from .result_location import ResultLocation


class ResultCatchment(ResultLocation):
    """
    Class for wrapping a single ResultData catchment.

    Parameters
    ----------
    catchment: IRes1DCatchment
        MIKE 1D IRes1DCatchment object.
    res1d : Res1D
        Res1D object the catchment belongs to.
    """

    def __init__(self, catchment, res1d):
        ResultLocation.__init__(self, catchment.DataItems, res1d)
        self._catchment = catchment
        self.set_quantities()
        self.set_static_attributes()

    def __repr__(self) -> str:
        return f"<Catchment: {self.id}>"

    def __getattribute__(self, __name: str):
        # TODO: Remove this in 1.0.0
        if __name == "catchment":
            warn(
                "Accessing IRes1DCatchment attribute via .catchment is deprecated. Use ._catchment."
            )
            return self._catchment
        try:
            return super().__getattribute__(__name)
        except AttributeError:
            if hasattr(self._catchment, __name):
                warn(
                    f"Accessing IRes1DCatchment attribute {__name} directly is deprecated. Use static attributes instead, or ._catchment.{__name}."
                )
                return getattr(self._catchment, __name)
            else:
                raise AttributeError(
                    f"'{self.__class__.__name}' object has no attribute '{__name}'"
                )

    def set_static_attributes(self):
        """Set static attributes. These show up in the html repr."""
        self.set_static_attribute("id", self._catchment.Id)
        self.set_static_attribute("area", self._catchment.Area)
        self.set_static_attribute("type", self._catchment.Type)

    def add_to_result_quantity_maps(self, quantity_id, result_quantity):
        """Add catchment result quantity to result quantity maps."""
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, self.result_quantity_map
        )

        catchment_result_quantity_map = (
            self.res1d.result_network.catchments.result_quantity_map
        )
        self.add_to_result_quantity_map(
            quantity_id, result_quantity, catchment_result_quantity_map
        )

        query = QueryDataCatchment(quantity_id, self._catchment.Id, validate=False)
        self.add_to_network_result_quantity_map(query, result_quantity)

    def get_query(self, data_item):
        """Get a QueryDataCatchment for given data item."""
        quantity_id = data_item.Quantity.Id
        catchment_id = self._catchment.Id
        query = QueryDataCatchment(quantity_id, catchment_id)
        return query
