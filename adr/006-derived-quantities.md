# ADR-006: Derived Quantities System

**Status:** Accepted
**Date:** 2023

## Context

Users frequently need quantities that are not stored directly in result files but can be computed from stored quantities — for example, water depth (from water level and bottom level) or flooding extent.

<!-- TODO: @Ryan — add context on motivation and design choices -->

## Decision

Provide an extensible `DerivedQuantity` base class. Default derived quantities (water depth, flooding, filling, Manning Q-Q, reach absolute discharge, water level above critical) are auto-registered per Res1D instance. Users can add custom derived quantities by subclassing `DerivedQuantity`.

## Alternatives Considered

- **Post-processing only**: Users compute derived values themselves after reading base quantities; error-prone and repetitive.
- **Pre-computed storage**: Store all derived quantities in result files; increases file size and limits flexibility.

## Consequences

- Common derived quantities available out of the box
- Computed on demand from base quantities
- Extensible — users can define and register custom quantities
- Integrates with the fluent API (ADR-005) — derived quantities appear alongside stored ones
