"""What a network reads through: where each series sits, and the file header.

:class:`~mikeio1d.network.Network` holds one of these and asks it two things:
what a location carries, and the series for some locations. A loader fills it
in; the network never sees the file format behind it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from collections.abc import Sequence
    from datetime import datetime
    from pathlib import Path

    from ._naming import Address

import pandas as pd

from ..res1d import Res1D
from ..quantities import TimeSeriesId
from ..quantities import TimeSeriesIdGroup
from ._policy import _NO_NAME_FILTER_EXTENSIONS
from ._policy import _suffix_of


@dataclass(frozen=True)
class _Series:
    """One timeseries: the file it is in, and its id within that file."""

    path: Path
    tsid: TimeSeriesId


def _open_for(path: Path, tsids: Sequence[TimeSeriesId]) -> Res1D:
    """Open a result file so that a read loads only these series' elements.

    ``Res1D`` loads the dynamic data of every element its filter lets through,
    and a filter naming only nodes lets no reach through. A reach loads all of
    its gridpoints, which is as fine as the filter goes.
    """
    nodes, reaches = [], []
    if _suffix_of(path) not in _NO_NAME_FILTER_EXTENSIONS:
        nodes = sorted({t.name for t in tsids if t.group == TimeSeriesIdGroup.NODE})
        reaches = sorted({t.name for t in tsids if t.group == TimeSeriesIdGroup.REACH})
    return Res1D(
        str(path),
        nodes=nodes,
        reaches=reaches,
        quantities=sorted({t.quantity for t in tsids}),
        derived_quantities=[],
    )


@dataclass(frozen=True)
class _Results:
    """What a network reads through: where each series sits, and the file header.

    Everything here comes from the file headers.

    Attributes
    ----------
    series : mapping of address to (mapping of str to _Series)
        Every location's series, by quantity ID. A location absent from it has
        none; one mapped to an empty dict carries nothing, which is every node
        of a MIKE 11 result.
    units : mapping of str to str
        Unit abbreviation per quantity ID, over the main file and companion.
    period : tuple of datetime
        First and last timestep of the main result file.
    """

    series: Mapping[Address, Mapping[str, _Series]]
    units: Mapping[str, str]
    period: tuple[datetime, datetime]

    @classmethod
    def empty(cls) -> _Results:
        """Results with no series at all, for a network that holds topology only."""
        return cls(series={}, units={}, period=(None, None))

    def quantities_at(self, address: Address) -> tuple[str, ...]:
        """Quantity IDs readable at one location; empty where it carries none."""
        return tuple(self.series.get(address, ()))

    def read(self, items: Sequence[tuple[Address, str]]) -> pd.DataFrame:
        """Read the given pairs, loading only them, one batched call per file.

        Each pair must be one :meth:`quantities_at` confirms. The frame has one
        column per pair, in order and keeping duplicates; each distinct series
        is read once however often it is asked for.
        """
        if not items:
            # Not the file's time index, which would load its dynamic data.
            return pd.DataFrame(index=pd.DatetimeIndex([], name="time"))

        series = [self.series[address][quantity] for address, quantity in items]

        # Grouped by file and de-duplicated within it.
        by_file: dict[Path, list[TimeSeriesId]] = {}
        for item in series:
            tsids = by_file.setdefault(item.path, [])
            if item.tsid not in tsids:
                tsids.append(item.tsid)

        columns: dict[tuple[Path, TimeSeriesId], pd.Series] = {}
        index = None
        for path, tsids in by_file.items():
            frame = _open_for(path, tsids).read(tsids, column_mode="timeseries")
            # Concatenating would align two different axes on their timestamps
            # and fill the gaps with NaN, rather than say the files disagree.
            if index is not None and not frame.index.equals(index):
                raise ValueError(
                    f"'{path}' does not share a time axis with the result "
                    f"file it was read alongside: {len(frame.index)} steps against "
                    f"{len(index)}, so the two are not from the same run."
                )
            index = frame.index
            for tsid, (_, column) in zip(tsids, frame.items()):
                columns[(path, tsid)] = column

        return pd.concat(
            [columns[(item.path, item.tsid)] for item in series],
            axis=1,
            keys=range(len(series)),
        )
