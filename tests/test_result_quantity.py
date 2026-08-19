"""Tests for mikeio1d.result_network.result_quantity.ResultQuantity."""

from types import SimpleNamespace

import pytest

from mikeio1d.result_network import ResultQuantity


@pytest.fixture
def quantity_outside_a_network():
    """A ResultQuantity that was never added to a ResultNetwork.

    Only data_item is read during construction, so the rest can be left unset.
    """
    data_item = SimpleNamespace(Quantity=SimpleNamespace(Id="WaterLevel"))
    return ResultQuantity(result_location=None, data_item=data_item, res1d=None)


def test_timeseries_id_raises_when_not_added_to_a_network(quantity_outside_a_network):
    """Accessing timeseries_id off a network must raise, not return None.

    The guard constructed the ValueError but never raised it, so the property
    fell through to `return self._timeseries_id` and handed back None.
    """
    with pytest.raises(ValueError, match="must be added to a ResultNetwork"):
        quantity_outside_a_network.timeseries_id
