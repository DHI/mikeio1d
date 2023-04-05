import numpy as np

from .custom_exceptions import NoDataForQuery
from .custom_exceptions import InvalidQuantity
from .custom_exceptions import InvalidStructure
from .various import NAME_DELIMITER


class QueryData:
    """
    Base query class that declares what data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'WaterLevel', 'Discharge', etc. Call res1d.quantities to get all quantities.
    name: str
        Name or ID of location under interest.
    validate: bool
        Flag specifying to validate the query.
    """

    def __init__(self, quantity, name=None, validate=True):
        self._name = name
        self._quantity = quantity

        if validate:
            self._validate()

    def _validate(self):
        if not isinstance(self.quantity, str):
            raise TypeError("Quantity must be a string.")

        if self.name is not None and not isinstance(self.name, str):
            raise TypeError("Argument 'name' must be either None or a string.")

    @staticmethod
    def from_dotnet_to_python(array):
        """Convert .NET array to numpy."""
        return np.fromiter(array, np.float64)

    @property
    def quantity(self):
        return self._quantity

    @property
    def name(self):
        return self._name

    def _check_invalid_quantity(self, res1d):
        if self._quantity not in res1d.quantities:
            raise InvalidQuantity(f"Undefined quantity {self._quantity}. "
                                  f"Allowed quantities are: {', '.join(res1d.quantities)}.")

    def _check_invalid_values(self, values):
        if values is None:
            raise NoDataForQuery(str(self))

    def __repr__(self):
        return NAME_DELIMITER.join([self._quantity, self._name])


class QueryDataReach(QueryData):
    """A query object that declares what reach data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'WaterLevel' or 'Discharge'. Call res1d.quantities to get all quantities.
    name: str
        Reach name.
    chainage: float
        Chainage value.
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataReach('WaterLevel', 'reach1', 10)` is a valid query.
    """

    def __init__(self, quantity, name=None, chainage=None, validate=True):
        super().__init__(quantity, name, validate=False)
        self._chainage = chainage

        if validate:
            self._validate()

    def _validate(self):
        super()._validate()

        if self.chainage is not None and not isinstance(self.chainage, (int, float)):
            raise TypeError("Argument 'chainage' must be either None or a number.")

        if self.name is None and self.chainage is not None:
            raise ValueError("Argument 'chainage' cannot be set if name is None.")

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        values = ( res1d.query.GetReachValues(name, chainage, quantity)
                   if chainage is not None else
                   res1d.query.GetReachStartValues(name, quantity) )

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)

    @property
    def chainage(self):
        return self._chainage

    def __repr__(self):
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        return ( NAME_DELIMITER.join([quantity, name, f'{chainage:g}'])
                 if chainage is not None else
                 NAME_DELIMITER.join([quantity, name]) )


class QueryDataNode(QueryData):
    """A query object that declares what node data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'WaterLevel' or 'Discharge'. Call res1d.quantities to get all quantities.
    name: str, optional
        Node name
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataNode('WaterLevel', 'node1')` is a valid query.
    """

    def __init__(self, quantity, name=None, validate=True):
        super().__init__(quantity, name, validate)

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        values = res1d.query.GetNodeValues(self._name, self._quantity)

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)


class QueryDataCatchment(QueryData):
    """A query object that declares what catchment data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'TotalRunoff'. Call res1d.quantities to get all quantities.
    name: str, optional
        Catchment name
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataCatchment('TotalRunoff', 'catchment1')` is a valid query.
    """

    def __init__(self, quantity, name=None, validate=True):
        super().__init__(quantity, name, validate)

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        values = res1d.query.GetCatchmentValues(self._name, self._quantity)

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)


class QueryDataGlobal(QueryData):
    """A query object that declares what global data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'TimeStep'. Call res1d.quantities to get all quantities.
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataGlobal('TimeStep')` is a valid query.
    """

    def __init__(self, quantity, validate=True):
        super().__init__(quantity, validate=validate)

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        data_item = res1d.global_data[self._quantity]
        values = data_item.CreateTimeSeriesData(0)

        self._check_invalid_values(values)

        return self.from_dotnet_to_python(values)

    def __repr__(self):
        return self._quantity


class QueryDataStructure(QueryDataReach):
    """A query object that declares what structure data to extract from a .res1d file.

    Parameters
    ----------
    quantity: str
        e.g. 'DischargeInStructure'. Call res1d.quantities to get all quantities.
    name: str
        Reach name where the structure is located.
    chainage: float
        Chainage value where the structure is located on reach.
    validate: bool
        Flag specifying to validate the query.

    Examples
    --------
    `QueryDataStructure('DischargeInStructure', 'structure1')` is a valid query.
    """

    def __init__(self, quantity, structure=None, name=None, chainage=None, validate=True):
        super().__init__(quantity, name, chainage, validate=validate)
        self._structure = structure

    def get_values(self, res1d):
        self._check_invalid_quantity(res1d)

        self._check_invalid_structure(res1d)
        result_structure = res1d.structures[self._structure]

        self._check_invalid_structure_quantity(result_structure)
        data_item = result_structure.get_data_item(self._quantity)

        values = data_item.CreateTimeSeriesData(0)

        self._check_invalid_values(values)

        self._update_location_info(result_structure)

        return self.from_dotnet_to_python(values)

    def _check_invalid_structure(self, res1d):
        if self._structure not in res1d.structures:
            raise InvalidStructure(str(self))

    def _check_invalid_structure_quantity(self, result_structure):
        if self._quantity not in result_structure.data_items_dict:
            raise InvalidQuantity(str(self))

    def _update_location_info(self, result_structure):
        if self._name is None:
            self._name = result_structure.reach.Name

        if self._chainage is None:
            self._chainage = result_structure.chainage

    def __repr__(self):
        structure = self._structure
        name = self._name
        chainage = self._chainage
        quantity = self._quantity

        if name is None and chainage is None:
            return NAME_DELIMITER.join([quantity, structure])

        if chainage is None:
            return NAME_DELIMITER.join([quantity, structure, name])

        return NAME_DELIMITER.join([quantity, structure, name, f'{chainage:g}'])
