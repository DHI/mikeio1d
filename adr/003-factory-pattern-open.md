# ADR-003: Factory Pattern for File Opening

**Status:** Accepted
**Date:** 2021

## Context

MIKE 1D files come in many formats: .res1d, .res, .resx, .out (EPANET/SWMM), and .xns11 (cross sections). Users shouldn't need to know which class to instantiate.

## Decision

Provide `mikeio1d.open()` as a single entry point that inspects the file extension and returns the appropriate handler (Res1D or Xns11). Mirrors mikeio's `mikeio.open()`.

## Alternatives Considered

- **Require users to pick the class**: Error-prone; file extensions alone don't always make the distinction obvious.
- **Single class for all formats**: Would lead to a monolithic class with many conditional branches.

## Consequences

- Simple, discoverable API: `mikeio1d.open("results.res1d")`
- File type detection is centralized
- New file types can be added without changing user code
