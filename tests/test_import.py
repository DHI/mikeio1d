import pytest
import warnings


def test_imports_without_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        import mikeio1d


def test_can_import_queries_from_res1d():
    from mikeio1d.res1d import QueryDataCatchment
    from mikeio1d.res1d import QueryDataNode
    from mikeio1d.res1d import QueryDataReach
    from mikeio1d.res1d import QueryDataStructure
    from mikeio1d.res1d import QueryDataGlobal


def test_can_import_mike1d_quantities_from_res1d():
    from mikeio1d.res1d import mike1d_quantities


def test_filter_package_imports_standalone():
    """Importing a filter submodule directly must not hit a circular import.

    The submodules used to reach ResultSubFilter through the package __init__,
    so they only worked while name_filter was listed after result_filter there.
    """
    from mikeio1d.filter.name_filter import NameFilter
    from mikeio1d.filter.quantity_filter import QuantityFilter
    from mikeio1d.filter.time_filter import TimeFilter


def test_res1d_exports_every_name_in_its_all():
    """Names in __all__ must exist at runtime, not only for type checkers."""
    import mikeio1d.res1d as res1d

    missing = [name for name in res1d.__all__ if not hasattr(res1d, name)]
    assert missing == []


def test_query_data_converter_reaches_query_data_at_runtime():
    """QueryData is called, not just annotated, so it needs a runtime import."""
    from mikeio1d.quantities import TimeSeriesId
    from mikeio1d.result_query.query_data_converter import QueryDataConverter

    timeseries_id = TimeSeriesId(quantity="WaterLevel", name="1", group="Node")

    QueryDataConverter.convert_time_series_id_to_query(timeseries_id)
