# mikeio1d Changelog

## [Unreleased]

## [0.2] - 2022-06-20

### Added

- Ability to read result files in a filtered way
- More detailed information about result files in __repr__
- Dictionaries containing catchment, node, reach, and global result item classes
- Support for reading SWMM and EPANET result files by upgrading to MIKE 1D v20.1.0

### Changed

- Use MIKE 1D NuGet packages v20.1.0
- Use pythonnet v3.0.0a2

### Fixed

- Fix data frame fragmentation error for res1d with many columns

### Removed

- .NET and native DHI libraries from source control

## [0.1] - 2021-05-05

### Added

- Reading of res1d and xns11 files into pandas data frames


[unreleased]: https://github.com/DHI/mikeio1d/compare/v0.2...HEAD
[0.2]: https://github.com/DHI/mikeio1d/releases/tag/v0.2
[0.1]: https://github.com/DHI/mikeio1d/releases/tag/v0.1
