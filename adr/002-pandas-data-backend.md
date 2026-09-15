# ADR-002: pandas DataFrames as Primary Data Container

**Status:** Accepted
**Date:** 2019 (inherited from mikeio)

## Context

MIKE IO 1D needs an in-memory representation for result data. mikeio uses numpy-backed Dataset/DataArray because DFS data is multi-dimensional and spatial. MIKE 1D results are fundamentally different — tabular time series for nodes, reaches, and catchments with no spatial dimensions.

## Decision

Use pandas DataFrames with DatetimeIndex as the primary data container.

## Alternatives Considered

- **numpy arrays (like mikeio)**: Less natural for tabular time series; users would need to track metadata separately.
- **Custom Dataset/DataArray**: Unnecessary complexity when pandas already fits the data shape.

## Consequences

- Natural fit for 1D time series data (one column per quantity/location)
- Familiar API for engineers already using pandas
- Leverages pandas' time handling, grouping, and aggregation
- Easy integration with plotting and analysis tools
