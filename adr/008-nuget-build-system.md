# ADR-008: NuGet-Based Build System

**Status:** Accepted
**Date:** 2022

## Context

.NET DLLs were committed to the repository from the initial commit. NuGet packages are the single source of truth for these binaries — vendoring copies in git created a redundant, hard-to-maintain mirror.

## Decision

Remove .NET DLLs from source control. Retrieve them via NuGet at build time using a hatch build hook. The build process also compiles a C# utility library (`DHI.Mike1D.MikeIO`) that provides helper functionality bridging Python and .NET.

## Alternatives Considered

- **Keep DLLs in repo**: Simple but duplicates the source of truth; repository bloat; version updates require manual file replacement.
- **System MIKE installation only**: Would complicate installation; not all users have MIKE installed.

## Consequences

- NuGet packages are the single source of truth for .NET binaries
- Cleaner repository without binary files in git history
- Version updates are a NuGet reference change, not a file swap
- Build requires network access to retrieve NuGet packages
- Supports both bundled binaries and system MIKE installations via `MIKE_INSTALL_PATH`
