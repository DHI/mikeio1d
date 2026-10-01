# ADR-009: Public API Boundary

**Status:** Accepted
**Date:** 2026

## Context

mikeio1d grew without saying which of its modules users may import, so everything looked public. Any change to internals risked being a breaking change, and the docs could drift from the code with nothing to catch it. Several packages are only the machinery behind `Res1D`, and some of them take or return .NET types.

## Decision

The public API is the names in each package's `__all__`, plus every non-underscore member of an exported class. A module whose name starts with a single underscore is private, along with everything in it. `scripts/lint_public_api.py` (`just api`) checks this against the source and the docs.

Existing packages that are only plumbing behind `Res1D` keep their names but declare `__all__ = []`, so no caller's import breaks. New internal code goes in underscore-prefixed modules (as `network/_network.py` does), so the name says it without an `__all__`.

### What is public

- `mikeio1d`: `Res1D`, `Xns11`, `open`.
- `network`: `Network`, `Address`, `NetworkLocation` and the rest of its `__all__`; its implementation sits in underscore modules.
- Everything reached from `Res1D` and `Xns11`: the result network (`result_network`), cross sections (`cross_sections`), geometry types, the `m1d` pandas accessor and its helpers, `quantities` (`TimeSeriesId`, `DerivedQuantity` for users to subclass), and the `mikenet.load*` functions.
- `experimental`: exported and documented, but labelled unstable in the API reference.

### What is internal, and why

A package is internal when users get its behaviour through `Res1D` or the network and collection methods, and it is only the machinery behind them:

- `filter`: every method takes or returns a .NET `ResultData` or `Filter`. Users filter through the `Res1D` arguments (`nodes=`, `time=`, …).
- `result_reader_writer`, `result_extractor`: the reading, merging and export behind `Res1D.read`, `merge`, `extract` and `to_csv`/`to_dfs0`/`to_txt`.
- `result_query`: the `QueryData` classes. `mikeio1d.query` still re-exports them as a legacy input to `Res1D.read`, but they are not the way forward; use `TimeSeriesId`.
- `geometry.geopandas`: the converters behind `to_geopandas()` (see [ADR-007](007-geodataframe-converters.md)).
- `quantities.derived.default_quantities`: `Res1D` registers the default derived quantities itself (see [ADR-006](006-derived-quantities.md)).
- `mikenet.LibraryLoaders`: an implementation detail of the `load*` functions.

### Escape hatches to .NET

Public signatures must not expose .NET (`DHI.*`, `System.*`) or private types, but some do on purpose, and those carry the comment `# api: allow-leaked-type`:

- Deliberate access to the underlying .NET object: `Res1D.data`, `result_data`, `query`, `searcher`; the `res1d_*` properties on result locations; `ResultQuantity.get_data_entry_net`; `CrossSection.m1d_cross_section`, `location`; `CrossSectionCollection.data`, `cross_section_data`, `interpolation_type`.
- Deprecated aliases of those properties, kept until they are removed: `ResultGridPoint.gridpoint` and `ResultStructure.reach` (use `res1d_gridpoint` and `res1d_reach`).
- Plumbing on a public class that cannot be renamed without breaking callers: `get_m1d_dataset`, `get_query`, `add_query`, `prettify_quantity`.
- Constructors only the package calls: the `Result*` and `CrossSection*` `__init__`s, and `Network.__init__` (users call `Network.open()`).

`git grep "api: allow-leaked-type"` lists them all. The marker records a decision; it is not a way to silence the linter for new code.

## Alternatives Considered

- **Rename internal packages with an underscore** (`_filter`, `_result_query`, …): The clearest signal, but it breaks every caller importing the old path, including the test suite. Rejected for existing packages; used for new ones.
- **Deprecate first, then rename**: More work for no gain while nothing prevents the imports anyway. It remains possible later.
- **Leave it undeclared**: Every change to internals stays a potential breaking change, and the docs can drift from the code unchecked.

## Consequences

- `__all__ = []` is a declaration, not enforcement: `from mikeio1d.filter import NameFilter` still works, and such names may change without a deprecation cycle.
- `leaked-type` only recognises .NET types and underscore-private names. A type from an `__all__ = []` package in a public signature is not caught, so keep such types off public signatures by review: take a plain value (a `str`, say) at the public seam and convert it inside.
