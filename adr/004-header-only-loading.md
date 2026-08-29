# ADR-004: Header-Only Loading by Default

**Status:** Accepted
**Date:** 2021 (option), 2024 (default)

## Context

MIKE 1D result files can contain millions of time steps across thousands of network elements. Loading all data eagerly wastes memory and time, especially when users only need a subset of the results.

## Decision

Load only file headers by default. Dynamic results are loaded on demand when `.read()` is called. Filtering by time, quantity, or location can be applied at open time to further limit what is loaded.

Header-only loading was introduced as an option in 2021. In 2024, it became the default behavior, complementing the fluent result network API (ADR-005) which lets users browse metadata and selectively read data.

## Alternatives Considered

- **Eager loading**: Simple but impractical for large files.
- **Explicit filter-only loading**: Requires users to know upfront what they need; less exploratory.

## Consequences

- Fast file opening regardless of file size
- Users can explore available quantities and locations without loading data
- Data loaded only when explicitly requested via `.read()`
- Filtering at open time enables efficient bulk reads of specific subsets
