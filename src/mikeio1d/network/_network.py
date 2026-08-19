"""A network of nodes and reaches, addressable by the names it came with.

Reading a result file gives locations named the way the model named them: a node
id, or a reach and a distance along it. A graph needs one flat set of integers.
:class:`Network` holds both, and :meth:`Network.find` and :meth:`Network.recall`
translate between them.
"""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any, overload

import networkx as nx
import numpy as np
import numpy.typing as npt
import pandas as pd
import xarray as xr

from ..res1d import Res1D
from ._companions import _companion_paths, _read_companions
from ._graph import _CHAINAGE_TOLERANCE, _build_dataframe, _generate_alias_map, _generate_graph
from ._policy import _validate_extension
from ._res1d import _load_res1d_network
from ._types import NetworkReach


class Network:
    """Network built from a set of reaches, with coordinate lookup and data access."""

    def __init__(self, reaches: Sequence[NetworkReach]):
        graph = _generate_graph(reaches)
        self._initialize_network_attributes(graph)
        self._reaches = self._generate_reaches_dict(reaches)

    def _initialize_network_attributes(self, graph: nx.Graph):
        self._alias_map = _generate_alias_map(graph)
        self._df = _build_dataframe(graph)
        self._graph = graph.copy()

    def __repr__(self) -> str:
        time = self._df.index
        time_window = "N/A - N/A" if len(time) == 0 else f"{time[0]} - {time[-1]}"
        out = [
            "<Network>",
            f"Reaches: {len(self._reaches)}",
            f"Nodes: {self._graph.number_of_nodes()}",
            f"Quantities: {self.quantities}",
            f"Time: {time_window}",
        ]
        return "\n".join(out)

    @classmethod
    def open(
        cls,
        res: str | Path | Res1D,
        *,
        companions: Sequence[str | Path | Res1D] | None = None,
        nodes: str | list[str] | None = None,
        reaches: str | list[str] | None = None,
        quantities: str | list[str] | None = None,
    ) -> Network:
        """Read a network from a result file.

        Parameters
        ----------
        res : str, Path or Res1D
            Path to a ``.res1d``, ``.res11`` or ``.res`` result file, or an
            already-opened :class:`~mikeio1d.Res1D`.
        companions : sequence of str, Path or Res1D, or None, optional
            Files read alongside the result and recognised by their extension:

            * ``.resx`` -- extra EPANET results for the same network. Its node
              quantities (tank ``Volume`` and ``Volume Percentage``) are merged
              onto the matching nodes, and its reach quantities (pump
              ``efficiency``, ``energy`` and ``energy costs``) onto the matching
              reach's breakpoints.
            * ``.inp`` -- the EPANET input file, read for its ``[PIPES]``
              lengths. No result file carries a reach length, so without this one
              no reach has one.

            ``None`` *(default)* looks for them beside the result file, matching
            its folder and stem; ``[]`` reads none; a list reads exactly those.
            Only EPANET results are looked for, since no other product writes
            companions this reader knows.
        nodes : str, list of str, or None, optional
            Controls which nodes have their timeseries data loaded into memory.

            * ``None`` *(default)* -- data is loaded for every node.
            * A single node ID or a list of node IDs -- only those nodes get
              data; others are topology-only.
            * ``[]`` (empty list) -- no node data is loaded at all.

            The full network topology is always constructed regardless of this
            setting, so ``find()`` and ``recall()`` still work on all nodes.
        reaches : str, list of str, or None, optional
            Controls which reaches have their intermediate gridpoint data
            populated.

            * ``None`` *(default)* -- gridpoints are populated for every reach.
            * A single reach name or a list of reach names -- only those reaches
              get gridpoint data; others are topology-only.
            * ``[]`` (empty list) -- no gridpoint data is loaded at all.

            EPANET reaches have at most one gridpoint (see Notes), but this
            argument still governs whether its data, and any matching ``.resx``
            reach quantities, are populated.
        quantities : str, list of str, or None, optional
            Controls which quantities are read at each selected location.

            * ``None`` *(default)* -- every quantity is read.
            * A single quantity name or a list of names -- only those are read.
            * ``[]`` (empty list) -- no data is read at all.

            A location that does not carry a requested quantity becomes
            topology-only rather than an error, so this composes with ``nodes``
            and ``reaches`` on files where nodes and reaches hold different
            quantities.

        Returns
        -------
        Network

        Raises
        ------
        NotImplementedError
            If no network can be built from the file's extension.
        ValueError
            If a companion has an extension this reader does not know, if two
            companions of the same kind are given, or if a ``.resx`` does not
            come from the same run as the result file.

        Examples
        --------
        >>> from mikeio1d.network import Network
        >>> network = Network.open("model.res1d")  # doctest: +SKIP

        Load data only for the two nodes where observations exist, and skip all
        intermediate gridpoint data to keep memory usage low:

        >>> network = Network.open(  # doctest: +SKIP
        ...     "model.res1d",
        ...     nodes=["node_a", "node_b"],
        ...     reaches=[],
        ... )

        Read a single quantity, for a calibration loop that only scores
        discharge:

        >>> network = Network.open("model.res1d", quantities="Discharge")  # doctest: +SKIP

        Name the companions rather than letting them be found:

        >>> network = Network.open(  # doctest: +SKIP
        ...     "model.res",
        ...     companions=["other.resx", "other.inp"],
        ... )

        Notes
        -----
        MIKE 11 keeps its timeseries on reach gridpoints rather than on nodes,
        so the nodes of a ``.res11`` network carry no data of their own. Pass
        ``reaches`` rather than ``nodes`` to control what gets loaded.

        EPANET is a link-node model, and mikeio1d reports a single synthetic
        gridpoint for each reach, not tied to either end. That gridpoint is
        duplicated into two breakpoints, one at each end of the reach, so its
        own quantities (``Flow``, ``Velocity``, ...) are reachable through
        :meth:`find` and :meth:`recall` the same way a MIKE reach's end data
        already is. As a result:

        * without the ``.inp``, a reach's length is unknown, so only its first
          breakpoint (``distance=0.0``) is real; the second is not addressable
          by distance at all -- ``find(reach=..., distance=...)`` resolves it
          only via ``distance="start"``/``"end"`` (which return the node, not
          the breakpoint), or not at all by a number. The corresponding edges of
          :attr:`graph` are ``length=None``
        * with the ``.inp``, a pipe's second breakpoint sits at its full length
          -- both breakpoints are then addressable by distance, and the edge
          between them carries the pipe's real length. Pumps and valves keep an
          unaddressable second breakpoint even so, since ``[PIPES]`` is the only
          section carrying lengths

        Node timeseries, :meth:`to_dataframe`, :meth:`to_dataset`,
        ``find(node=...)`` and :meth:`recall` are unaffected.
        """
        if isinstance(res, (str, Path)):
            path = Path(res)
            _validate_extension(path.suffix)
            res = Res1D(str(path))
        elif isinstance(res, Res1D):
            _validate_extension(Path(res.file_path).suffix)
        else:
            raise TypeError(f"Expected a str, Path or Res1D object, got {type(res).__name__!r}")

        if nodes is None:
            nodes_list: list[str] = list(res.nodes.keys())
        elif isinstance(nodes, str):
            nodes_list = [nodes]
        else:
            nodes_list = list(nodes)

        if reaches is None:
            reaches_list: list[str] = list(res.reaches.keys())
        elif isinstance(reaches, str):
            reaches_list = [reaches]
        else:
            reaches_list = list(reaches)

        # None is threaded through as "read everything" rather than expanded to
        # res.quantities, which would only cost a lookup for the same result.
        if quantities is None:
            quantities_set: set[str] | None = None
        elif isinstance(quantities, str):
            quantities_set = {quantities}
        else:
            quantities_set = set(quantities)

        found, discovered = _companion_paths(res, companions)

        try:
            extra, lengths = _read_companions(res, found)
            list_of_reaches = _load_res1d_network(
                res,
                nodes_list,
                reaches_list,
                extra=extra,
                lengths=lengths,
                quantities=quantities_set,
            )
        except ValueError as err:
            if not discovered:
                raise
            # A companion nobody asked for must be named when it fails, or the
            # error points at files the caller did not know were being read.
            names = ", ".join(f"'{Path(str(companion)).name}'" for companion in found)
            raise ValueError(
                f"Failed to build a network from '{Path(str(res.file_path)).name}': {err}\n"
                f"Companion files read alongside it, because they share its folder: "
                f"{names}. Pass companions=[] to read the result file on its own, or "
                "name the companions you want."
            ) from err

        return cls(list_of_reaches)

    @staticmethod
    def _generate_reaches_dict(
        reaches: Sequence[NetworkReach],
    ) -> dict[str, NetworkReach]:
        return {r.id: r for r in reaches}

    def to_dataframe(self, sel: str | None = None) -> pd.DataFrame:
        """Dataframe using node ids as column names.

        It will be multiindex unless 'sel' is passed.

        Parameters
        ----------
        sel : Optional[str], optional
            Quantity to select, by default None

        Returns
        -------
        pd.DataFrame
            Timeseries contained in graph nodes
        """
        df = self._df.copy()
        if sel is None:
            return df
        else:
            df.attrs["quantity"] = sel
            return df.reorder_levels(["quantity", "node"], axis=1).loc[:, sel]

    def _identity_coords(self, nodes: npt.ArrayLike) -> dict[str, tuple[str, np.ndarray]]:
        """Describe each node by the name it had before it became an integer.

        Parameters
        ----------
        nodes : array-like of int
            The integer ids to describe, in the order they appear.

        Returns
        -------
        dict
            ``name``, ``reach`` and ``distance`` arrays along the ``node``
            dimension. A node fills in ``name`` and leaves the other two empty; a
            breakpoint fills in ``reach`` and ``distance`` and leaves ``name``
            empty. Nothing carries both, so the empty half says which it is.
        """
        aliases = {node_id: alias for alias, node_id in self._alias_map.items()}

        names, reaches, distances = [], [], []
        for node in np.asarray(nodes):
            alias = aliases[int(node)]
            if isinstance(alias, tuple):
                reach, distance = alias
                names.append("")
                reaches.append(reach)
                distances.append(np.nan if distance is None else distance)
            else:
                names.append(alias)
                reaches.append("")
                distances.append(np.nan)

        return {
            "name": ("node", np.array(names, dtype=str)),
            "reach": ("node", np.array(reaches, dtype=str)),
            "distance": ("node", np.array(distances, dtype=float)),
        }

    def to_dataset(self) -> xr.Dataset:
        """Dataset of the timeseries, with each node's original identity alongside.

        Returns
        -------
        xr.Dataset
            One variable per quantity over ``(time, node)``. ``node`` is the
            integer index the graph uses, and the ``name``, ``reach`` and
            ``distance`` coordinates carry the names the model gave the same
            locations, so a consumer never has to hold on to the network to know
            what a column is::

                Coordinates:
                  * time      datetime64
                  * node      int64     0 1 2 3 ...
                    name      <U16      'J1' 'J2' '' ''
                    reach     <U16      '' '' 'r1' 'r1'
                    distance  float64   nan nan 0.0 24.5

            Empty when no location carries data.
        """
        df_raw = self.to_dataframe()
        if len(df_raw.columns) == 0:
            return xr.Dataset()
        df = df_raw.reorder_levels(["quantity", "node"], axis=1)
        quantities = df.columns.get_level_values("quantity").unique()
        ds = xr.Dataset(
            {
                q: xr.DataArray(df[q], dims=["time", "node"], attrs={"long_name": str(q)})
                for q in quantities
            }
        )
        return ds.assign_coords(self._identity_coords(ds.node.values))

    @property
    def graph(self) -> nx.Graph:
        """Graph of the network."""
        return self._graph

    @property
    def quantities(self) -> list[str]:
        """Quantities present in data.

        Returns
        -------
        List[str]
            List of quantities
        """
        return list(self.to_dataframe().columns.get_level_values(1).unique())

    @overload
    def find(
        self,
        *,
        node: str,
        reach: None = None,
        distance: None = None,
    ) -> int:
        pass

    @overload
    def find(
        self,
        *,
        node: list[str],
        reach: None = None,
        distance: None = None,
    ) -> list[int]:
        pass

    @overload
    def find(
        self,
        *,
        node: None = None,
        reach: str | list[str],
        distance: str | float,
    ) -> int:
        pass

    @overload
    def find(
        self,
        *,
        node: None = None,
        reach: str | list[str],
        distance: list[str | float],
    ) -> list[int]:
        pass

    def find(
        self,
        node: str | list[str] | None = None,
        reach: str | list[str] | None = None,
        distance: str | float | list[str | float] | None = None,
    ) -> int | list[int]:
        """Find node or breakpoint id in the Network object based on former coordinates.

        Parameters
        ----------
        node : str | List[str], optional
            Node id(s) in the original network, by default None
        reach : str | List[str], optional
            Reach id(s) for breakpoint lookup or reach endpoint lookup, by default None
        distance : str | float | List[str | float], optional
            Distance(s) along reach for breakpoint lookup, or "start"/"end"
            for reach endpoints, by default None

        Returns
        -------
        int | List[int]
            Node or breakpoint id(s) in the generic network

        Raises
        ------
        ValueError
            If invalid combination of parameters is provided
        KeyError
            If requested node/breakpoint is not found in the network
        """
        by_node = node is not None
        by_breakpoint = reach is not None or distance is not None

        if by_node and by_breakpoint:
            raise ValueError(
                "Cannot specify both 'node' and 'reach'/'distance' parameters simultaneously"
            )

        if not by_node and not by_breakpoint:
            raise ValueError("Must specify either 'node' or both 'reach' and 'distance' parameters")

        ids: list[str | tuple[str, float]]

        if by_node:
            assert node is not None
            if not isinstance(node, list):
                node = [node]
            ids = list(node)

        else:
            if reach is None or distance is None:
                raise ValueError(
                    "Both 'reach' and 'distance' parameters are required for breakpoint/endpoint lookup"
                )

            if not isinstance(reach, list):
                reach = [reach]

            if not isinstance(distance, list):
                distance = [distance]

            if len(reach) == 1:
                reach = reach * len(distance)

            if len(reach) != len(distance):
                raise ValueError(
                    "Incompatible lengths of 'reach' and 'distance' arguments. One 'reach' admits multiple distances, otherwise they must be the same length."
                )

            ids = []
            for reach_i, distance_i in zip(reach, distance):
                if distance_i in ["start", "end"]:
                    if reach_i not in self._reaches:
                        raise KeyError(f"Reach '{reach_i}' not found in the network.")

                    network_reach = self._reaches[reach_i]
                    if distance_i == "start":
                        ids.append(network_reach.start.id)
                    else:
                        ids.append(network_reach.end.id)
                else:
                    if not isinstance(distance_i, (int, float)):
                        raise ValueError(
                            "Invalid 'distance' value for breakpoint lookup: "
                            f"{distance_i!r}. Expected a numeric value or 'start'/'end'."
                        )
                    ids.append((reach_i, distance_i))

        def _resolve_id(id):
            if id in self._alias_map:
                return self._alias_map[id]
            if isinstance(id, tuple):
                reach_id, distance = id
                for key, val in self._alias_map.items():
                    if (
                        isinstance(key, tuple)
                        and key[0] == reach_id
                        and key[1] is not None
                        and abs(key[1] - distance) <= _CHAINAGE_TOLERANCE
                    ):
                        return val
            return None

        resolved = [_resolve_id(id) for id in ids]
        missing_ids = [ids[i] for i, v in enumerate(resolved) if v is None]
        if missing_ids:
            raise KeyError(
                f"Node/breakpoint(s) {missing_ids} not found in the network. Available nodes are {set(self._alias_map.keys())}"
            )
        if len(resolved) == 1:
            return resolved[0]
        return resolved

    @overload
    def recall(self, id: int) -> dict[str, Any]:
        pass

    @overload
    def recall(self, id: list[int]) -> list[dict[str, Any]]:
        pass

    def recall(self, id: int | list[int]) -> dict[str, Any] | list[dict[str, Any]]:
        """Recover the original coordinates of an element given the node id(s) in the Network object.

        Parameters
        ----------
        id : int | List[int]
            Node id(s) in the generic network

        Returns
        -------
        Dict[str, Any] | List[Dict[str, Any]]
            Original coordinates. For single input returns dict, for multiple inputs returns list of dicts.
            Dict contains coordinates:
            - For nodes: 'node' key with node id
            - For breakpoints: 'reach' and 'distance' keys with reach id and distance

        Raises
        ------
        KeyError
            If node id is not found in the network
        ValueError
            If node id string format is invalid
        """
        if not isinstance(id, list):
            id = [id]

        reverse_alias_map = {v: k for k, v in self._alias_map.items()}

        results: list[dict[str, Any]] = []
        for node_id in id:
            if node_id not in reverse_alias_map:
                raise KeyError(f"Node ID {node_id} not found in the network.")

            key = reverse_alias_map[node_id]
            if isinstance(key, str):
                results.append({"node": key})
            else:
                results.append({"reach": key[0], "distance": key[1]})

        if len(results) == 1:
            return results[0]
        else:
            return results

    def copy(self) -> Network:
        """Create a deep copy of the Network.

        Returns
        -------
        Network
            Deep copy of the Network object
        """
        return deepcopy(self)
