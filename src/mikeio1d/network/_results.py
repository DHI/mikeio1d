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

    Addressed by :class:`~mikeio1d.quantities.TimeSeriesId` rather than by the
    ``ResultQuantity`` it came from. Loading a companion's dynamic data replaces
    the whole ``ResultNetwork`` it hangs off (see ``ResultReader._load_file``),
    so any quantity object captured before that point is a stale handle onto a
    discarded object graph. A ``TimeSeriesId`` is inert, and every read looks it
    up afresh.
    """

    res: Res1D
    tsid: TimeSeriesId


@dataclass(frozen=True)
class _Results:
    """What a network reads through: where each series sits, and the file header.

    Everything here comes from the headers, so holding it costs nothing, and a
    network keeps one for as long as it can read. It is shared rather than
    copied when the network is, since the ``Res1D`` its series point into holds
    .NET objects that cannot be deep-copied.

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

        Each pair is one :meth:`quantities_at` has confirmed, under the network's
        own spelling of the location. The frame has one column per pair, in
        order and keeping duplicates, and each distinct series is read once
        however often it was asked for - an EPANET reach's two break points name
        the same gridpoint, so asking for both is one read, not two.
        """
        if not items:
            # Nothing asked for, nothing opened. The file's own time index would
            # be the tidier index to carry here, but reading it loads the whole
            # of the file's dynamic data, which is the one thing asking for
            # nothing should not do.
            return pd.DataFrame(index=pd.DatetimeIndex([], name="time"))

        series = [self.series[alias][quantity] for alias, quantity in items]

        # Grouped by file, and within a file de-duplicated, so what crosses the
        # interop boundary is each distinct series exactly once.
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
