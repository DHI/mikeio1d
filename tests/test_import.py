import importlib
import sys
import warnings

import pytest


def test_python_patch_version_is_supported(monkeypatch):
    import mikeio1d

    original_version_info = sys.version_info
    try:
        monkeypatch.setattr(sys, "version_info", (3, 15, 2))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.reload(mikeio1d)
        assert not any("officially supports Python" in str(w.message) for w in caught)
    finally:
        monkeypatch.setattr(sys, "version_info", original_version_info)
        importlib.reload(mikeio1d)


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
