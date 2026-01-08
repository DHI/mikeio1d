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


@pytest.mark.parametrize(
    "requires_python, boundary",
    [
        (">=3.9,<=3.13", (3, 13)),
        ("<=3.13,>=3.9", (3, 13)),
        (">=3.9,<3.13", (3, 12)),
        ("<3.13,>=3.9", (3, 12)),
    ],
)
def test_read_python_upper_boundary(requires_python, boundary):
    from mikeio1d import python_upper_boundary

    assert python_upper_boundary(requires_python) == boundary
