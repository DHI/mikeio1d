"""Module for the Xns11 class."""

from __future__ import annotations

from collections import defaultdict, namedtuple
from pathlib import Path
from warnings import warn

import pandas as pd
from DHI.Mike1D.CrossSectionModule import CrossSectionData, CrossSectionDataFactory
from DHI.Mike1D.Generic import Connection, Diagnostics, Location

from .cross_sections import CrossSection, CrossSectionCollection


def read(file_path: str | Path, queries: QueryData | list[QueryData]) -> pd.DataFrame:
    """Read the requested data from the xns11 file and return a Pandas DataFrame.

    Parameters
    ----------
    file_path: str
        full path and file name to the xns11 file.
    queries: a single query or a list of queries
        `QueryData` objects that define the requested data.

    Returns
    -------
    pd.DataFrame

    """
    queries = queries if isinstance(queries, list) else [queries]
    with open(file_path) as xns11:
        return xns11.read(queries)


def open(file_path: str | Path) -> Xns11:
    """Open a xns11 file as a Xns11 object.

    Has convenient methods to extract specific data from the file.
    It is recommended to use it as a context manager.

    Parameters
    ----------
    file_path: str
        full path and file name to the xns11 file.

    Returns
    -------
    Xns11

    Examples
    --------
    >>> with open("file.xns11") as x11:
    >>>     print(x11.topoid_names)
    ['topoid1', 'topoid2']

    """
    return Xns11(file_path)


class Xns11:
    """A class to read and write xns11 files.

    Parameters
    ----------
    file_path: str or Path, optional
        full path and file name to the xns11 file.

    Examples
    --------
    ```python
    # Open an existing file
    >>> xns = Xns11("file.xns11")

    # Overview of the cross sections
    >>> xns.xsections.to_dataframe()

    # Read a specific cross section
    >>> xs = xns.xsections.sel(location_id='basin_left1', chainage='122.042', topo_id='1')

    # Plot a cross section
    >>> xs.plot()

    # Access cross section raw data
    >>> xs.raw_data

    # Access cross section processed data
    >>> xs.processed_data
    ```

    """

    def __init__(self, file_path: str | Path = None):
        self._cross_section_data = None
        self._cross_section_data_factory = CrossSectionDataFactory()
        self._xsections = None

        self.file_path = self._validate_file_path(file_path)
        self._load_or_create_cross_section_data()
        self._init_xsections()

    def __repr__(self):
        """Return a string representation of the object."""
        return "<mikeio1d.Xns11>"

    def _validate_file_path(self, file_path: str | Path | None) -> Path | None:
        """Validate user supplied file path, return a Path object if valid."""
        # file path is not strictly required (e.g. creating a new xns11 file)
        if not file_path:
            return None

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return file_path

    def _load_or_create_cross_section_data(self) -> None:
        """Initialize the CrossSectionData object."""
        if self.file_path:
            self._cross_section_data = self._cross_section_data_factory.Open(
                Connection.Create(str(self.file_path)), Diagnostics("Error loading file.")
            )
        else:
            self._cross_section_data = CrossSectionData()

    def _init_xsections(self) -> None:
        """Initialize the cross sections."""
        self._xsections = CrossSectionCollection()
        self._xsections.xns11 = self
        for xs in self._cross_section_data:
            self.xsections.add_xsection(CrossSection(xs))

    @staticmethod
    def get_supported_file_extensions() -> set[str]:
        """Get supported file extensions for Xns11."""
        return {".xns11"}

    @staticmethod
    def from_cross_section_collection(xsections: CrossSectionCollection) -> Xns11:
        """Create a Xns11 object from a CrossSectionCollection."""
        xns = Xns11()
        for key in xsections:
            xs = xsections[key]
            xns.add_xsection(xs)

        return xns

    def info(self):
        """Print information about the result file."""
        info = self._get_info()
        print(info)

    def _get_info(self) -> str:
        info = []
        info.append(f"# Cross sections: {str(len(self.xsections))}")
        info.append(f"Interpolation type: {str(self.interpolation_type)}")
        info = str.join("\n", info)
        return info

    @property
    def xsections(self):
        """
        A collection of CrossSection objects.

        The collection is a dict-like object where the keys are tuples of location ID, chainage and topo ID.

        Examples
        --------
        >>> location_id, chainage, topo_id = 'location', '200.000', 'topo'

        #### Get a specific cross section
        >>> xns.xsections[location_id, chainage, topo_id]

        #### Get all cross sections for a particular location and topo.
        >>> xns.xsection[location_id, ..., topo_id]
        """
        return self._xsections

    @property
    def interpolation_type(self):
        """Defines how an interpolated cross section are interpolated.

        Returns
        -------
        DHI.Mike1D.CrossSectionModule.XSInterpolationType

            Possible values:
            - ProcessedTopDown: 0
                Interpolates the processed data. Raw data will not be available.
            - Raw: 1
                Interpolates the raw data and calculates processed data from the new raw data.
            - Middling: 2
                Interpolation happens during runtime by requesting values at neighbour cross sections and interpolate between those.

        """
        return self._cross_section_data.XSInterpolationType

    @property
    def _topoids(self):
        return list(self._cross_section_data.GetReachTopoIdEnumerable())

    @property
    def topoid_names(self):
        """A list of the topo-id names."""
        return [topoid.TopoId for topoid in self._topoids]

    @property
    def _reaches(self):
        return list(self._cross_section_data.GetReachTopoIdEnumerable())

    @property
    def reach_names(self):
        """A list of the reach names."""
        return [reach.ReachId for reach in self._topoids]

    def add_xsection(self, cross_section: CrossSection):
        """Add a cross section to the file."""
        self.xsections.add_xsection(cross_section)

    def write(self, file_path: str | Path = None):
        """Write data to the file."""
        file_path = file_path if file_path else self.file_path

        if not file_path:
            raise ValueError("A file path must be provided.")

        file_path = Path(file_path)
        if not file_path.suffix == ".xns11":
            raise ValueError("The file extension must be .xns11.")

        current_con_path = Path(self._cross_section_data.Connection.FilePath.Path)
        if not file_path.exists() or not current_con_path.resolve().samefile(file_path.resolve()):
            self._cross_section_data.Connection = Connection.Create(str(file_path))

        self._cross_section_data_factory.Save(self._cross_section_data)

        if not self.file_path:
            self.file_path = file_path

    @staticmethod
    def _topoid_in_reach(self, reach):
        """List topo-IDs contained in a reach."""
        return [
            r.TopoId
            for r in list(self.file.GetReachTopoIdEnumerable())
            if reach.ReachId == r.ReachId
        ]

    @staticmethod
    def _chainages(reach):
        """List chainages of a reach topo-ID combination."""
        return [r.Key for r in list(reach.GetChainageSortedCrossSections())]

    def _get_values(self, points):
        df = pd.DataFrame()
        p = zip(points["chainage"], points["reach"], points["topoid"])
        for chainage, reach, topoid in p:
            location = Location()
            location.ID = reach.value
            location.Chainage = chainage.value
            geometry = self._cross_section_data.FindClosestCrossSection(
                location, topoid.value
            ).BaseCrossSection.Points
            x, z = [], []
            for i in range(geometry.Count):
                x.append(geometry.LstPoints[i].X)
                z.append(geometry.LstPoints[i].Z)
            x_name = f"x {topoid.value} {reach.value} {chainage.value}"
            z_name = f"z {topoid.value} {reach.value} {chainage.value}"
            geometry_x = pd.Series(x, name=x_name)
            geometry_z = pd.Series(z, name=z_name)
            df = pd.concat([df, geometry_x, geometry_z], axis=1)
        return df

    def _get_data(self, points):
        df = self._get_values(points)
        return df

    def _validate_queries(self, queries, chainage_tolerance=0.1):
        """Check whether the queries point to existing data in the file."""
        for q in queries:
            if q.topoid_name not in self.topoid_names:
                raise ValueError(f"Topo-id '{q.topoid_name}' was not found.")
            if q.reach_name is not None:
                if q.reach_name not in self.reach_names:
                    raise ValueError(f"Reach '{q.reach_name}' was not found.")
                else:
                    found_topo_id_in_reach = False
                    for reach in self._reaches:
                        if found_topo_id_in_reach:
                            break
                        # Look for the targeted reach
                        if q.reach_name != reach.ReachId:
                            continue
                        # Raise an error if the combination reach and topo-id does not exist
                        topoid_names_in_reach = self._topoid_in_reach(self, reach)
                        if q.topoid_name not in topoid_names_in_reach:
                            raise ValueError(
                                f"Topo-ID '{q.topoid_name}' was not found in reach '{q.reach_name}'."
                            )
                        found_topo_id_in_reach = True
            if q.chainage is not None:
                found_chainage = False
                for reach in self._reaches:
                    if found_chainage:
                        break
                    # Look for the targeted combination reach and topo-id
                    if q.reach_name != reach.ReachId and q.topoid_name != reach.TopoId:
                        continue
                    for chainage in self._chainages(reach):
                        # Look for the targeted chainage
                        chainage_diff = chainage - q.chainage
                        if abs(chainage_diff) < chainage_tolerance:
                            found_chainage = True
                            break
                if not found_chainage:
                    raise ValueError(
                        f"Chainage {q.chainage} was not found in reach '{q.reach_name}' for Topo-ID '{q.topoid_name}'."
                    )

    def _build_queries(self, queries):
        built_queries = []
        for q in queries:
            # e.g. QueryData("topoid1", "reach1", 58.68)
            if q.reach_name and q.chainage:
                built_queries.append(q)
                continue
            # e.g QueryData("topoid1", "reach1") or QueryData("topoid1")
            q_topoid_name = q.topoid_name
            q_reach_name = q.reach_name
            for reach, reach_name in zip(self._reaches, self.reach_names):
                if q_reach_name is not None:  # When reach_name is set
                    if reach_name != q_reach_name:
                        continue
                topoid_in_reach = self._topoid_in_reach(self, reach)
                if q.topoid_name not in topoid_in_reach:
                    continue
                for curr_chain in self._chainages(reach):
                    if reach.TopoId == q.topoid_name:
                        chainage = curr_chain
                    else:
                        continue

                    q = QueryData(q_topoid_name, reach_name, round(chainage, 3))
                    built_queries.append(q)
        return built_queries

    def _find_points(self, queries, chainage_tolerance=0.1):
        PointInfo = namedtuple("PointInfo", ["index", "value"])

        found_points = defaultdict(list)
        # Find the points given its topo-id, reach, and chainage
        for q in queries:
            for reach_idx, curr_reach in enumerate(self._reaches):
                # Look for the targed reach and topo-id
                if q.reach_name != curr_reach.ReachId or q.topoid_name != curr_reach.TopoId:
                    continue
                reach_info = PointInfo(reach_idx, q.reach_name)
                topo_pair = self._topoid_in_reach(self, curr_reach)
                for topoid_reach_idx, topoid_reach in enumerate(topo_pair):
                    if q.topoid_name != topoid_reach:
                        continue
                    topoid_info = PointInfo(topoid_reach_idx, topoid_reach)
                    for idx, curr_chain in enumerate(self._chainages(curr_reach)):
                        # Look for the targed chainage
                        chainage_diff = curr_chain - q.chainage
                        is_chainage = abs(chainage_diff) < chainage_tolerance
                        if not is_chainage:
                            continue
                        # idx is the index in the topoid
                        chainage_info = PointInfo(idx, q.chainage)
                        found_points["chainage"].append(chainage_info)
                        found_points["topoid"].append(topoid_info)
                        found_points["reach"].append(reach_info)
                        break  # Break at the first chainage found.

        return dict(found_points)

    def read(self, queries):
        """Read the requested data from the xns11 file and return a Pandas DataFrame.

        Parameters
        ----------
        queries: list
            `QueryData` objects that define the requested data.

        Returns
        -------
        pd.DataFrame

        """
        self._validate_queries(queries)
        built_queries = self._build_queries(queries)
        found_points = self._find_points(built_queries)
        df = self._get_data(found_points)
        return df

    # region Deprecated methods
    # These methods will be removed in the next major release.

    @property
    def file(self):
        """Alias for CrossSectionData objected stored on the member '_cross_section_data'."""
        warn("The 'file' property is deprecated. Use '_cross_section_data' instead.")
        return self._cross_section_data

    def __enter__(self):
        """Context manager enter method."""
        warn("Using Xns11 as a context manager is deprecated. Files are automatically closed.")
        return self

    def __exit__(self, *excinfo):
        """Context manager exit method."""
        pass

    def close(self):
        """Close the file handle."""
        warn("The 'close' method is deprecated. Files are automatically closed.")
        self.__del__()

    # endregion


class QueryData:
    """A query object that declares what data should be extracted from a .xns11 file.

    Parameters
    ----------
    topoid_name: str
        Topo ID, must be passed
    reach_name: str, optional
        Reach name, consider all the reaches if None
    chainage: float, optional
        chainage, considers all the chainages if None

    Examples
    --------
    >>> QueryData('topoid1', 'reach1', 10) # is a valid query.
    >>> QueryData('topoid1', 'reach1')     # requests all the points for `topoid1` of `reach1`.
    >>> QueryData('topoid1') requests all the points for `topid1` of the file.

    """

    def __init__(self, topoid_name, reach_name=None, chainage=None):
        self._topoid_name = topoid_name
        self._reach_name = reach_name
        self._chainage = chainage
        self._validate()

    def _validate(self):
        tp = self.topoid_name
        rn = self.reach_name
        c = self.chainage
        if not isinstance(tp, str):
            raise TypeError("topoid_name must be a string.")
        if rn is not None and not isinstance(rn, str):
            raise TypeError("reach_name must be either None or a string.")
        if c is not None and not isinstance(c, (int, float)):
            raise TypeError("chainage must be either None or a number.")
        if rn is None and c is not None:
            raise ValueError("chainage cannot be set if reach_name is None.")

    @property
    def topoid_name(self):
        """Topo ID."""
        return self._topoid_name

    @property
    def reach_name(self):
        """Reach name."""
        return self._reach_name

    @property
    def chainage(self):
        """Chainage."""
        return self._chainage

    def __repr__(self):
        """Return a string representation of the object."""
        return (
            f"QueryData(topoid_name='{self.topoid_name}', "
            f"reach_name='{self.reach_name}', "
            f"chainage={self.chainage})"
        )


__all__ = ["Xns11"]
