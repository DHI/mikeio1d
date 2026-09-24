"""What a network reads through: where each series sits, and the file header.

:class:`~mikeio1d.network.Network` holds one of these and asks it two things:
what a location carries, and the series for some locations. A loader fills it
in; the network never sees the file format behind it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime

    from ..res1d import Res1D
    from ..quantities import TimeSeriesId
    from ._naming import Alias


@dataclass(frozen=True)
class _Series:
    """One timeseries, and the file it has to be read from.

    Addressed by :class:`~mikeio1d.quantities.TimeSeriesId` rather than by a
    ``ResultQuantity``: loading a file's dynamic data replaces the
    ``ResultNetwork`` a quantity hangs off (see ``ResultReader._load_file``),
    which would leave a captured quantity stale.
    """

    res: Res1D
    tsid: TimeSeriesId


@dataclass(frozen=True)
class _Results:
    """What a network reads through: where each series sits, and the file header.

    Everything here comes from the file headers.

    Attributes
    ----------
    series : mapping of alias to (mapping of str to _Series)
        Every location's series, by quantity ID. A location absent from it has
        none; one mapped to an empty dict carries nothing, which is every node
        of a MIKE 11 result.
    units : mapping of str to str
        Unit abbreviation per quantity ID, over the main file and companion.
    period : tuple of datetime
        First and last timestep of the main result file.
    """

    series: Mapping[Alias, Mapping[str, _Series]]
    units: Mapping[str, str]
    period: tuple[datetime, datetime]

    @classmethod
    def empty(cls) -> _Results:
        """Results with no series at all, for a network that holds topology only."""
        return cls(series={}, units={}, period=(None, None))

    def quantities_at(self, alias: Alias) -> tuple[str, ...]:
        """Quantity IDs readable at one location; empty where it carries none."""
        return tuple(self.series.get(alias, ()))

    def read(self, items: Sequence[tuple[Alias, str]]) -> pd.DataFrame:
        """Read the given pairs, one batched call per file they live in.

        Each pair must be one :meth:`quantities_at` confirms. The frame has one
        column per pair, in order and keeping duplicates; each distinct series
        is read once however often it is asked for.
        """
        if not items:
            # Not the file's time index, which would load its dynamic data.
            return pd.DataFrame(index=pd.DatetimeIndex([], name="time"))

        series = [self.series[alias][quantity] for alias, quantity in items]

        # Grouped by file and de-duplicated within it.
        by_file: dict[int, tuple[Res1D, list[TimeSeriesId]]] = {}
        for item in series:
            _, tsids = by_file.setdefault(id(item.res), (item.res, []))
            if item.tsid not in tsids:
                tsids.append(item.tsid)

        columns: dict[tuple[int, TimeSeriesId], pd.Series] = {}
        index = None
        for res, tsids in by_file.values():
            frame = res.read(tsids, column_mode="timeseries")
            # Concatenating would align two different axes on their timestamps
            # and fill the gaps with NaN, rather than say the files disagree.
            if index is not None and not frame.index.equals(index):
                raise ValueError(
                    f"'{res.file_path}' does not share a time axis with the result "
                    f"file it was read alongside: {len(frame.index)} steps against "
                    f"{len(index)}, so the two are not from the same run."
                )
            index = frame.index
            for tsid, (_, column) in zip(tsids, frame.items()):
                columns[(id(res), tsid)] = column

        return pd.concat(
            [columns[(id(item.res), item.tsid)] for item in series],
            axis=1,
            keys=range(len(series)),
        )
