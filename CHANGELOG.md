# mikeio1d Changelog

## [Unreleased]

### Added
- `mikeio1d.network`: build a graph-shaped `Network` from a result file, with
  `Network.open`, `Network.reaches`, `to_networkx`, `to_dataframe`/`to_dataset`, and the
  EPANET `.resx` companion. Needs the new `network` extra
  (`pip install mikeio1d[network]`).
- `Network.period`, `Network.quantities`, `Network.resolve`, `Network.addresses` and
  `Network.read`, for asking a result file what it holds and reading only the series a
  caller turns out to need, by the names the model used - a node ID, or a reach and a
  position along it. A read loads only the variables it asks for, each as its whole time
  series (#250).
- `Network.read(quantity=...)` reads one quantity at every location that carries it (#250).
- `Network.open` takes a `Res1D` opened with `nodes=`, `reaches=` or `quantities=` as the
  whole network, carrying only the series its filter lets through. It used to fail with a
  bare `KeyError` on the first reach whose end node the filter left out. A `Res1D` opened with
  `time=` or `step_every=` raises `NotImplementedError` (#250).
- Every public member of `mikeio1d.network` has an example that runs as a doctest (#250).
- Network user guide section covering how a result file becomes a graph, with a diagram of the
  mapping and a note on why a zero-length boundary edge is free to cross.
- A single location (node, reach, catchment, structure) takes a `quantities` argument on
  `read`/`to_dataframe`, and gains `add`, `plot`, `to_csv`, `to_dfs0` and `to_txt` taking the
  same argument. An unknown quantity raises `ValueError` rather than falling back to every
  queued series (#155).

### Fixed
- Reach `start_node` and `end_node` no longer fail for a `Res1D` opened with a `Path`.
- `Res1D.to_dfs0` no longer fails for an output file given as a `Path`.
- `ResultQuantity.timeseries_id` now raises instead of silently returning `None` when the quantity is not attached to a `ResultNetwork` (#248).
- Reach geometry no longer accumulates for the lifetime of the process; the cached points and
  distances now live on the `ReachGeometry` object and are freed with it (#248).
- `Res1D.to_txt` and `Res1D.to_csv` no longer leave the output file open when a write fails (#248).

### Changed
- `Network.open` reads the header and the topology and no timeseries. `to_dataframe` and
  `to_dataset` read every location when they are called. The
  `nodes`, `reaches` and `quantities` options are gone: read the locations you need with
  `Network.read` instead (#250).
- `Network.quantities` now names what can be read somewhere in the network, mapped to its
  unit. Membership and `sorted()` read as before; indexing does not (#250).
- A `.resx` carrying a quantity its `.res` already has at the same location is refused
  however the network is read. It used to be refused only where a frame was built, and
  otherwise read silently from the `.resx` (#250).
- `Network.resolve` answers with a `NetworkLocation` - its `address`, the `quantities`
  readable there and its graph integer `graph_node` - or `None`. It is the one lookup by name;
  `graph.nodes[graph_node]["address"]` goes back (#250).
- `Network.period` is a property, like `Network.quantities` (#250).
- `Network.to_dataframe` labels its columns `(address, quantity)`, as `Network.read` does,
  and its `sel` option is gone: read one quantity with `Network.read(quantity=...)`. `to_dataset`'s integer dimension is named
  `graph_node`, and its coordinate for a model node's id `node_id` (#250).
- `Network.graph` is now the method `Network.to_networkx()`, which builds a new graph the
  caller is free to edit on each call. `Network.copy` and `Network.release` are gone (#250).
- A place along a reach is a `position`, not a `distance`:
  `NetworkReach.start_position` and `end_position`, the `position_tol` argument of `resolve`
  and `read`, and `to_dataset`'s `position` coordinate (#250).
- A reach's `start` and `end` are its end nodes' ids; `NetworkNode` is gone.
  `NetworkLocation` and `NetworkReach` are exported from `mikeio1d.network` (#250).
- `ReachBreakpoint` is gone: `NetworkReach.breakpoints` holds the breakpoints' addresses,
  `(reach_id, position)` pairs that `Network.read` takes as they are (#250).
- A position past the last breakpoint of a reach of unknown length, such as an EPANET pump's
  far end, is refused with a message saying why, rather than one inviting a wider
  `position_tol` (#250).
- A reach of unknown length has one breakpoint, at its start, rather than one at each end:
  its far end has no known position. The EPANET test network has 36 graph nodes where it had
  37, since pump `9` has no length (#250).
- EPANET reach lengths are read from the `.res` itself, so a pipe has its end address without
  the `.inp`. The `.inp` is no longer a companion: `Network.open` does not look for it, and
  refuses one passed in `companions` with a `ValueError` (#250).
- `Network.read` snaps each item's position only onto a breakpoint carrying the item's
  quantity, so a caller need not know the grid is staggered to choose a `position_tol`.
  `Network.resolve` takes `quantity=` to do the same, and answers `None` exactly when `read`
  would refuse. A position within 1e-3 of a breakpoint names it, is given back in the file's
  spelling, and is never snapped away from it; `position_tol` only widens that window, and is
  checked on every call (#250).
- `Network.open` refuses a result holding catchments and no reaches, which used to open as an
  empty network. Catchments beside a network are left out with a warning naming their
  quantities, since a catchment has no address in a network (#250).
- Linting is pinned to ruff 0.16 and type hints use built-in generics throughout (#248).
- The `docs` and `experimental` dependency groups no longer repeat `xarray` and `networkx`;
  both are synced with `--extra network`, which is now the only place the pair is declared.

### Removed
- `experimental.NetworkMapper` and `experimental.GenericNetwork`, replaced by `mikeio1d.network`.
- `network.BasicNode`, `network.BasicReach`, and building a `Network` from a sequence of reaches.
  A `Network` is now built with `Network.open`, which is how anything ever used it. The
  abstract element classes are gone too: `Network.reaches` holds plain frozen records with the
  same attributes (#250; #257 tracks bringing it back).
- `Network.find` and `Network.recall`. Every member takes the model's names, `resolve` gives the
  graph integer for one, and each graph node's `address` attribute names it. A reach's end nodes
  are `reaches[reach_id].start` and `.end`, rather than `distance="start"`/`"end"` (#250).

## [1.3.1] - 2026-07-15

### Fixed
- Reading PRF files containing pumps with IDs differing only by case (e.g. `my_pump` and `MY_PUMP`) no longer crashes (#245).

## [1.3.0] - 2026-06-26

This is primarily a maintenance release, bundling a few cross-section bug fixes and updated Python version support.

### Added
- Support for Python 3.14

### Fixed
- Cross-section conveyance now respects the resistance type, deferring computation to the MIKE 1D engine with a MIKE+ consistent fallback (#229).
- Resistance values now persist correctly when set via the raw setter, including ZONES distribution (#233).
- Datum is now applied to processed cross-section levels (#236).

### Changed
- Restructured package into a src/ layout (#243).

### Removed
- Support for Python 3.10 and 3.11. MIKE IO 1D now follows [Scientific Python SPEC 0](https://scientific-python.org/specs/spec-0000/) for the supported Python range (#238).

## [1.2.0] - 2026-05-20

### Added
- More helpful error messages when indexing reach gridpoints.
- If reach index does not exist as integer, automatically tries float chainage (e.g. 1000 tries chainage 1000.0)
- Export to Networkx graphs (experimental - see mikeio1d.experimental)
- Export to Xarray DataArray (experimental - see mikeio1d.experimental)
- Export to XVec DataArray (experimental - see mikeio1d.experimental)

### Fixed
- Pandas 3.0 compatibility
- Some static properties failing for EPANET result files
- Quantity filter for not predefined MIKE 1D quantities
- Filtering on opening Res1D no longer requires single values to be in list.
- Res1D now accepts quantities specified as strings

### Changed
- xarray and networkx are now optional dependencies (install separately for experimental features)
- Relaxed pythonnet version upper boundary

### Removed
- Support for Python 3.9 (end of service life)


## [1.1.1] - 2025-06-02

### Added
- Added support for indexing ResultReach with float chainage values

## [1.1.0] - 2025-06-01

### Added
- Added to_dataframe() method alias for read() in multiple classes for API consistency

## [1.0.4] - 2025-05-21

### Fixed
- Creating Res1D objects with pathlib.Path is now possible (same as mikeio.open)

## [1.0.3] - 2025-02-17

### Fixed
- Update MIKE 1D binaries for MIKE+ 2025, solving some issues with reading res/resx files created with MIKE+ 2025.

## [1.0.2]  - 2025-01-14

### Fixed
- Matplotlib is now included as a dependency, avoiding import errors on fresh install

## [1.0.1]  - 2025-01-13

### Fixed
- Res1D can now be saved when it was loaded using filters

## [1.0.0]  - 2024-12-19

### Changed

- Removed all code marked for deprecation in versions < 1.0

## [0.10.0] - 2024-12-19

### Added

- New step_every filter when loading Res1D files (e.g. load every 'i'th time step)
- New quantity filter when loading Res1D files (e.g. load only specific quantities)
- Update notebook on working with large files for the new filters.
- Support for Python 3.13
- Add Res1D.result_type property.

### Fixed

### Changed

- Result plots now have gridlines by default.
- Names no longer show up on ResultLocations html repr (i.e. cleaner notebooks)
- Refactored Res1D.network and associated objects.
- Refactored Res1D static attributes.
- Xns11 is now a CrossSectionCollection (i.e. no longer needed to use Xns11.xsections)
- Refactored filters.
- Res1D.data is now an alias to the more explicit Res1D.result_data
- CrossSectionCollection.data is now an alias to the more explicit CrossSectionCollection.cross_section_data
- Updated documentation.

## [0.9.1] - 2024-11-12

### Added

### Fixed

- Fixed bug where ResultLocations.quantities errored if the quantity id contained a space.

### Changed

### [0.9.0] - 2024-11-06

### Added

- Create Res1D/Xns11 objects using mikeio1d.open().
- Filter dynamic data loaded in time now with mikeio1d.Res1d(..., time=(start,end)).
- Added some new notebook examples for Res1D.
- Add additional linting rules for documentation, numpy, and pandas.

### Fixed

- Autocompletion was flaky when accessing objects with many dots.
- Improved docstring consistency throughout codebase.

### Changed

- Updated notebooks to latest scripting API and reorganized.
- Only load header by default (performance improvement).
- Reduce calls to pythonnet (performance improvement).
- Speed up CI tests.
- Clean Res1D scripting API, adding deprecation warnings.
- Use Ruff instead of black for formatting and linting.

### [0.8.2] - 2024-10-14

### Fixed

- Derived quantities were missing from object html representations.

### [0.8.1] - 2024-10-14

### Fixed

- Wheel and source builds did not include all necessary binary dependencies.

## [0.8.0] - 2024-10-14

### Added

- Derived quantity concept introduced with an API the same as regular quantities.
- Nine default derived quantities (e.g. 'Node Flooding', 'Reach Filling', etc.).
- Ability to extend MIKE IO 1D with custom derived quantities.
- Quantity units are now more consistently visible in object representations.

### Fixed

- Fixed bug where rounding to milliseconds sometimes failed.

### Changed

- Updated documentation and README examples.


## [0.7.0] - 2024-09-19

### Added

- New API for reading and writing xns11 files (see new notebook examples).
- Access to both raw and processed data in xns11 files.
- Export xns11 sections and markers to GeoPandas.
- Gridpoint indexing from ResultReach by either chainage or number.
- Extra gridpoint static attributes: chainage, reach name, and x/y coordinates.

### Fixed

- Various warning fixes related to new Pandas and GeoPandas versions.

### Changed

- Removed support for Python 3.8 (to be compatible with Pandas >= 2.1).
- Iterating over IRes1DReach objects must now be done via ResultReach.reaches.


## [0.6.1] - 2024-03-23

### Fixed

- Loading MIKE IO 1D together with MIKE+Py
- Fixed override_name parameter that was not working in ResultFrameAggregator
- Fixed converting res11 to res1d
- Fixed calling ResultQuantityCollection.plot with kwargs

## [0.6] - 2024-02-08

### Added

- Introduced TimeSeriesId to uniquely identify results.
- Read methods now include 'column_mode' parameter that enables multiindex reading (e.g. column_mode='compact').
- Added more type hints to improve IDE auto-completion and docstring peeking.
- Merging of regular and LTS extreme/periodic res1d files.
- Convert reaches to GeoPandas in two modes: 'segmented' and 'combined'.
- Export to GeoPandas with quantities aggregated in time.

### Changed

- Result reading/writing fundamentally uses TimeSeriesId now instead of QueryData
- DataFrames previously including duplicates are now resolved by TimeSeriesId (especially for reach segments, the 'tag' level is used)
- Following are now abstract base classes: ResultReader, QueryData, ResultLocation
- GeoPandas conversion now includes extra columns matching some TimeSeriesId fields.

## [0.5] - 2023-12-22

### Added

- Support for Python 3.12
- Linux support (experimental).
- Initial support for GeoPandas (ability to export static network)
- Geometry package for converting IRes1DLocation objects to corresponding Shapely objects
- Updated documentation hosted on GitHub Pages.

### Fixed

### Changed

- Consistent and pythonic test file structure

## [0.4.1] - 2023-12-14

### Added

- mikenet module for easier work with DHI .NET libraries.

### Fixed

- Res1D filtering for reaches inside MIKE 1D itself.

### Changed

- Use MIKE 1D NuGet packages v22.0.3 and v22.0.4 for DHI.Mike1D.ResultDataAccess

## [0.4] - 2023-09-14

### Added

- DHI.Mike1D.MikeIO C# utility and ResultReaderCopier for more performant reading of result files

### Changed

- Made ResultQuantity.plot method more Matplotlib-like

### Fixed

- Reading of MOUSE results files: CRF, PRF, and XRF
- Include milliseconds from .res1d files

### Removed

- Support for Python 3.6

## [0.3] - 2023-04-21

### Added

- Ability to add queries using auto-completion
- Ability to modify res1d file contents using a data frame
- Ability to extract time series to csv, dfs0, and txt files
- Support for querying structures and global data items

### Changed

- Use MIKE 1D NuGet packages v21.0.0

## [0.2] - 2023-03-14

### Added

- Ability to read result files in a filtered way
- More detailed information about result files in __repr__
- Dictionaries containing catchment, node, reach, and global result item classes
- Support for reading SWMM and EPANET result files by upgrading to MIKE 1D v20.1.0
- Support for reading LTS result files

### Changed

- Use MIKE 1D NuGet packages v20.1.0
- Use Python.NET v3.0.1

### Fixed

- Fix data frame fragmentation error for res1d with many columns

### Removed

- .NET and native DHI libraries from source control

## [0.1] - 2021-05-05

### Added

- Reading of res1d and xns11 files into pandas data frames


[unreleased]: https://github.com/DHI/mikeio1d/compare/v1.3.1...HEAD
[1.3.1]: https://github.com/DHI/mikeio1d/releases/tag/v1.3.1
[1.3.0]: https://github.com/DHI/mikeio1d/releases/tag/v1.3.0
[1.2.0]: https://github.com/DHI/mikeio1d/releases/tag/v1.2.0
[1.1.1]: https://github.com/DHI/mikeio1d/releases/tag/v1.1.1
[1.1.0]: https://github.com/DHI/mikeio1d/releases/tag/v1.1.0
[1.0.4]: https://github.com/DHI/mikeio1d/releases/tag/v1.0.4
[1.0.3]: https://github.com/DHI/mikeio1d/releases/tag/v1.0.3
[1.0.2]: https://github.com/DHI/mikeio1d/releases/tag/v1.0.2
[1.0.1]: https://github.com/DHI/mikeio1d/releases/tag/v1.0.1
[1.0.0]: https://github.com/DHI/mikeio1d/releases/tag/v1.0.0
[0.10.0]: https://github.com/DHI/mikeio1d/releases/tag/v0.10.0
[0.9.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.9.1
[0.9.0]: https://github.com/DHI/mikeio1d/releases/tag/v0.9.0
[0.8.2]: https://github.com/DHI/mikeio1d/releases/tag/v0.8.2
[0.8.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.8.1
[0.8.0]: https://github.com/DHI/mikeio1d/releases/tag/v0.8.0
[0.7.0]: https://github.com/DHI/mikeio1d/releases/tag/v0.7.0
[0.6.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.6.1
[0.6]: https://github.com/DHI/mikeio1d/releases/tag/v0.6
[0.5]: https://github.com/DHI/mikeio1d/releases/tag/v0.5
[0.4.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.4.1
[0.4]: https://github.com/DHI/mikeio1d/releases/tag/v0.4
[0.3]: https://github.com/DHI/mikeio1d/releases/tag/v0.3
[0.2]: https://github.com/DHI/mikeio1d/releases/tag/v0.2
[0.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.1
