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
