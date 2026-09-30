# ADR-005: Fluent Result Network API with Auto-Completion

**Status:** Accepted
**Date:** 2023

## Context

Early versions required users to construct query objects manually to access results. This was cumbersome and not discoverable — users had to know the exact quantity names, location IDs, and chainages upfront.

## Decision

Introduce a hierarchical fluent API with IDE auto-completion:

```python
res = mikeio1d.open("results.res1d")
res.nodes['node_id'].WaterLevel.read()
res.reaches['reach_id'][chainage].Discharge.read()
```

Dynamic attribute generation provides auto-completion for location IDs and quantity names. The access pattern follows: ResultNetwork → ResultNodes/ResultReaches/ResultCatchments → individual location → quantities.

<!-- TODO: @Ryan — add context on design inspiration and how this evolved -->

## Alternatives Considered

- **Keep query-based access only**: Less discoverable; no auto-completion support.
- **String-based indexing**: Would work but loses the benefit of IDE auto-completion for quantity names.

## Consequences

- Discoverable API that works with IDE and Jupyter tab completion
- Users can explore available data interactively
- Works naturally with header-only loading (ADR-004) — browse metadata, then read
- Largest subsystem in the codebase (~10+ modules in `result_network/`)
