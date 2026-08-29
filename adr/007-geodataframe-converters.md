# ADR-007: GeoDataFrame Converter Pattern

**Status:** Accepted
**Date:** 2023 (initial), 2024 (refactored)

## Context

Users need to visualize and analyze network results spatially. geopandas is the standard for geospatial tabular data in Python but is a heavy dependency that not all users need.

<!-- TODO: @Ryan — add context on the refactoring from monolithic to separate converters -->

## Decision

Provide separate converter classes per location type: nodes (points), reaches (lines), and catchments (polygons). geopandas is an optional dependency with guarded imports — the package works without it.

## Alternatives Considered

- **Single converter class**: Simpler initially but mixes different geometry types (points, lines, polygons) in one class.
- **Built-in geopandas dependency**: Would force installation of GDAL/geopandas for all users.

## Consequences

- Clean separation by geometry type (points, lines, polygons)
- geopandas users get spatial analysis capabilities
- Core functionality works without geopandas installed
- Each converter handles the specific geometry and metadata of its location type
