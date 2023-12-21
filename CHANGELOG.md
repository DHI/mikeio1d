# mikeio1d Changelog

## [Unreleased]

### Added

- Linux support.

### Fixed

### Changed

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


[unreleased]: https://github.com/DHI/mikeio1d/compare/v0.4...HEAD
[0.4.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.4.1
[0.4]: https://github.com/DHI/mikeio1d/releases/tag/v0.4
[0.3]: https://github.com/DHI/mikeio1d/releases/tag/v0.3
[0.2]: https://github.com/DHI/mikeio1d/releases/tag/v0.2
[0.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.1
