# ADR-001: pythonnet for .NET Interop

**Status:** Accepted
**Date:** 2019 (inherited from mikeio), kept at 2021 split

## Context

MIKE IO 1D reads results from DHI's MIKE 1D engine, which is built on .NET. Res1d originally lived inside mikeio, which used pythonnet for all .NET interop. When mikeio migrated its DFS layer to mikecore (a C/C++ rewrite) to enable Linux support and simplify installation, the 1D code was split into its own package (May 2021). Unlike DFS file formats, MIKE 1D's .NET API surface is large and complex — result data access, cross sections, network topology, filters — making a C rewrite impractical. The .NET dependency is inherent to MIKE 1D.

## Decision

Use pythonnet as the bridge to .NET MIKE 1D libraries. Bundle the required .NET DLLs in `mikeio1d/bin/` (later moved to NuGet retrieval, see ADR-008). Conversion utilities in `dotnet.py` handle type mapping between Python/numpy and .NET (datetime, arrays).

## Consequences

- Access to the full MIKE 1D .NET API from Python
- Cross-platform support requires .NET Runtime (8.0 on Linux)
- New Python version support depends on pythonnet releases
- 64-bit only (checked on import)
