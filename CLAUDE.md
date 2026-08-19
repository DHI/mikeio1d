# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MIKE IO 1D is a Python package for reading and manipulating MIKE 1D result files (res1d, res, resx, out, xns11 formats). It uses .NET interoperability via `pythonnet` to access DHI MIKE 1D libraries bundled in `src/mikeio1d/bin/`.

The package is fundamentally a Python wrapper around the [DHI MIKE 1D .NET library](https://docs.mikepoweredbydhi.com/engine_libraries/mike1d/mike1d_api/). The key .NET namespaces are `DHI.Mike1D.ResultDataAccess`, `DHI.Mike1D.Generic`, and `DHI.Mike1D.CrossSectionModule`. The .NET assemblies (version 23.0.3) are downloaded from NuGet at install time and placed in `src/mikeio1d/bin/`.

**Requirements:** Python 3.12–3.14 (64-bit only), `uv` package manager, .NET 8.0 Runtime (Linux) or VC++ redistributables (Windows).

## Commands

**Always run `uv sync` first** before running tests or other commands. This triggers the hatch build hook that downloads the DHI .NET DLLs into `src/mikeio1d/bin/`.

If the binaries have been removed (e.g. via `git clean -dxf src/mikeio1d/bin`), `uv sync` alone won't re-download them — use `--reinstall` to force the hook to run again:

```bash
uv sync --reinstall --group dev --group test --group notebooks --python 3.13
```

```bash
# Install dev dependencies (use highest supported version, currently 3.14)
# Uses --group (PEP 735 dependency-groups), not --extra
uv sync --group dev --group test --group notebooks --python 3.13

# Run all tests
uv run pytest

# Run a single test file or test
uv run pytest tests/test_res1d.py -v
uv run pytest tests/test_res1d.py::test_name -v

# Run optional dependency tests
uv run pytest -m optional_dependency

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

The local `.pytest.ini` excludes slow tests and experimental tests by default. CI uses `.pytest-ci.ini`.

## Architecture

### Entry Points

- `mikeio1d.open(filename)` — factory function returning `Res1D` or `Xns11`
- `mikeio1d.Res1D` — reads network/catchment result files (`.res1d`, `.res`, `.resx`, `.out`, `.prf`, etc.)
- `mikeio1d.Xns11` — reads/writes cross-section geometry files (`.xns11`)

### Core Submodule Map

| Submodule | Purpose |
|---|---|
| `result_network/` | Network structure: `ResultNetwork`, `ResultNode`, `ResultReach`, `ResultCatchment`, `ResultStructure` |
| `result_reader_writer/` | File I/O, merging result files |
| `result_query/` | Query builder for extracting time series |
| `filter/` | Time, name, and quantity filtering |
| `quantities/` | `TimeSeriesId` — identifies a time series; derived quantities |
| `cross_sections/` | `CrossSection`, `CrossSectionCollection` geometry |
| `geometry/` | Geographic coordinate/projection support (optional geopandas) |
| `pandas_extension/` | Custom pandas accessor (`.mikeio1d` namespace on DataFrames) |
| `experimental/` | Optional NetworkX graph and xarray integrations |
| `mikenet/` | .NET library loader |
| `dotnet.py` | .NET interop utilities |
| `bin/` | Bundled DHI .NET DLLs (downloaded from NuGet at install time) |
| `util/DHI.Mike1D.MikeIO/` | C# utility project — compiled at install, output goes to `bin/DHI.Mike1D.MikeIO/` |

### Data Flow

`Res1D` uses `pythonnet` to load the .NET libraries in `bin/`, then exposes result data through a lazy-loading `ResultNetwork` tree. Calling `.read()` or accessing a quantity via the network tree returns a pandas DataFrame. Filtering is applied via the `filter/` module before reading.

### C# Utility Library (`util/DHI.Mike1D.MikeIO/`)

A small C# project that is compiled during `uv sync` (via `scripts/util_builder.py`) and placed at `src/mikeio1d/bin/DHI.Mike1D.MikeIO/DHI.Mike1D.MikeIO.dll`. It provides utilities that are awkward to implement purely in Python against the .NET API:

| Class | Purpose |
|---|---|
| `ResultMerger` | Merges multiple `.res1d` files end-to-end |
| `LTSResultMerger*` | Specialized mergers for LTS (Long-Term Statistics) result types |
| `ResultDataCopier` | Copies result data between `ResultData` objects |
| `ResultDataExtensions` | Extension methods on `ResultData` |
| `DataEntry` | Helpers for reading individual data entries |

**To rebuild manually** (e.g. after changing the C# source or upgrading .NET SDK):

```bash
# NuGet assemblies must already be in src/mikeio1d/bin/ first
dotnet build --configuration Release util/DHI.Mike1D.MikeIO/DHI.Mike1D.MikeIO.csproj
# Then copy the output (or just re-run the full install):
python scripts/install_dependencies.py
```

### Test Data

Tests use fixtures from `tests/testdata/` (accessed via a generated `testdata` module with path constants). Expected DataFrames are stored as `.parquet` files in `tests/testdata/expected_results/` for regression testing with `assert_frame_equal`.

## Code Style

- Line length: 100 characters
- Ruff with numpy-style docstrings (PD, NPY, FA, D rules)
- Formatter: `ruff format`

### Imports

Import order is maintained by hand. Ruff's `I` (isort) rule is in `lint.ignore`,
because the order within a group is semantic rather than alphabetical and isort has
no sort key that reproduces it — every configuration tried reorders around 500 lines.
When adding an import, follow the file you are editing.

- Usually one name per line. A short combined import is fine — there are eight in the
  package — but never the parenthesised multi-line form the formatter produces. There
  are none, and adding one is what tips a whole block into being resorted.
- `from __future__ import annotations` first, then a `TYPE_CHECKING` block if the
  module needs one, then stdlib, third-party, and the package's own modules.
- `DHI.*` and `System` come last, in a group of their own separated by a blank line.
  They are .NET assemblies loaded through pythonnet rather than ordinary Python
  packages, and keeping them apart makes a module's interop surface obvious.
- Within a group, put related modules together and the more central ones first.

`src/mikeio1d/result_network/result_reach.py` is the worked example:

```python
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..res1d import Res1D
    from ..geometry import ReachGeometry
    from .result_quantity import ResultQuantity

    from DHI.Mike1D.ResultDataAccess import IDataItem
    from DHI.Mike1D.ResultDataAccess import IRes1DReach
    from DHI.Mike1D.ResultDataAccess import IRes1DGridPoint

import numpy as np

from ..various import try_import_shapely, DELETE_VALUE
from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup
from ..dotnet import pythonnet_implementation as impl

from .result_location import ResultLocation
from .result_location import ResultLocationCreator
from .result_gridpoint import ResultGridPoint
from .various import make_proper_variable_name

from DHI.Mike1D.ResultDataAccess import Res1DGridPoint
from DHI.Mike1D.ResultDataAccess import Res1DCircularCrossSection
from DHI.Mike1D.ResultDataAccess import Res1DEggshapedCrossSection
from DHI.Mike1D.ResultDataAccess import Res1DRectangularCrossSection
from DHI.Mike1D.Generic import Quantity
from DHI.Mike1D.Generic import PredefinedQuantity
```

Alphabetical sorting would get three things wrong here: `..various` leads because the
module is used throughout, `.result_location` precedes `.result_gridpoint` because a
reach is a location before it is a set of grid points, and `Res1DGridPoint` leads the
DHI block ahead of the cross-section types.

## Troubleshooting

**CLR / `BadImageFormatException` when loading DLLs**

Some files in `src/mikeio1d/bin/` (e.g. `DHI.Chart.Map.dll`) are native (non-.NET) DLLs. `mikenet.load_all()` skips them with a warning; individual `load_*` calls on a native DLL will also warn and skip. If a _managed_ assembly fails to load, the most common cause is stale or mismatched DLLs — force a clean reinstall:

```bash
uv sync --reinstall --group dev --group test --python 3.13
```

**`DHI.Mike1D.MikeIO` import error**

The internal C# utility DLL at `src/mikeio1d/bin/DHI.Mike1D.MikeIO/` is built from source at install time. If it's missing or was compiled against a different assembly version, rebuild it:

```bash
dotnet build --configuration Release util/DHI.Mike1D.MikeIO/DHI.Mike1D.MikeIO.csproj
python scripts/install_dependencies.py  # copies DLL to correct location
```

**pythonnet / Python version issues**

Use Python 3.12–3.14 (64-bit). Check `pythonnet>=3.0.0` is installed.
