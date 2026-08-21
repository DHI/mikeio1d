"""Abstract network elements, and the simplest concrete pair.

A reader supplies nodes, reaches and breakpoints; :class:`~mikeio1d.network.Network`
takes them and knows nothing about the file they came from. The abstract classes
here are that contract, and :class:`BasicNode`/:class:`BasicReach` are enough to
build a network by hand or in a test.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class NetworkNode(ABC):
    """Abstract base class for a node in a network.

    A node represents a discrete location in the network (e.g. a junction
    or reservoir) that carries time-series data for one or more physical
    quantities.

    Two properties must be implemented:

    * :attr:`id` - a unique string identifier for the node.
    * :attr:`data` - a time-indexed :class:`pandas.DataFrame` whose columns
      are quantity names.

    The concrete helper :class:`BasicNode` is provided for the common case
    where the data is already available as a DataFrame.

    See Also
    --------
    BasicNode : Ready-to-use concrete implementation.
    NetworkReach : Connects two NetworkNode instances.
    Network : Container that assembles nodes and reaches into a graph.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique string identifier for this node."""

    @property
    @abstractmethod
    def data(self) -> pd.DataFrame:
        """Time-indexed DataFrame with one column per quantity."""

    @property
    def quantities(self) -> list[str]:
        """List of quantity names available at this node."""
        return list(self.data.columns)


class ReachBreakPoint(ABC):
    """Abstract base class for an intermediate break point along a network reach.

    Break points represent locations between the start and end nodes of a
    reach (e.g. cross-section chainage points along a river reach) that carry
    their own time-series data.

    Two properties must be implemented:

    * :attr:`id` - a ``(reach_id, distance)`` tuple that uniquely locates the
      break point within the network. ``distance`` may be ``None`` when the
      break point's position along the reach is genuinely unknown (e.g. a
      link-node reach with no known length).
    * :attr:`data` - a time-indexed :class:`pandas.DataFrame` whose columns
      are quantity names.

    The :attr:`distance` convenience property returns ``id[1]`` (the position
    along the reach in the units used by the parent network, or ``None`` if
    unknown). It need not be measured from the start node: a MIKE river reach
    reports its chainage, which is a coordinate along the whole branch, so the
    distance from the start node is ``distance - reach.start_distance``. A
    break point with an unknown distance cannot be looked up via
    ``find(reach=..., distance=<number>)``, but is still reachable through
    ``ReachObservation`` and ``recall()``.

    Examples
    --------
    Minimal subclass:

    >>> class MyBreakPoint(ReachBreakPoint):
    ...     def __init__(self, reach_id, chainage, df):
    ...         self._id = (reach_id, chainage)
    ...         self._data = df
    ...     @property
    ...     def id(self): return self._id
    ...     @property
    ...     def data(self): return self._data

    See Also
    --------
    NetworkReach : Owns a list of ReachBreakPoint instances.
    NetworkNode : Represents a start/end node of a reach.
    Network : Assembles reaches (and their break points) into a graph.
    """

    @property
    @abstractmethod
    def id(self) -> tuple[str, float | None]:
        """``(reach_id, distance)`` tuple uniquely identifying this break point."""

    @property
    @abstractmethod
    def data(self) -> pd.DataFrame:
        """Time-indexed DataFrame with one column per quantity."""

    @property
    def distance(self) -> float | None:
        """Position along the reach, in the reach's own frame, or None if unknown."""
        return self.id[1]

    @property
    def quantities(self) -> list[str]:
        """List of quantity names available at this break point."""
        return list(self.data.columns)


class NetworkReach(ABC):
    """Abstract base class for a reach in a network.

    A reach represents a directed connection between two :class:`NetworkNode`
    instances (e.g. a river reach between two junctions).  It may also carry
    a list of :class:`ReachBreakPoint` objects for intermediate chainage
    locations.

    Subclass this to integrate your own network topology.  Four properties
    must be implemented:

    * :attr:`id` - a unique string identifier for the reach.
    * :attr:`start` - the upstream/start :class:`NetworkNode`.
    * :attr:`end` - the downstream/end :class:`NetworkNode`.
    * :attr:`breakpoints` - list of :class:`ReachBreakPoint` instances ordered
      by increasing distance from the start node (empty list if none).

    :attr:`length` is optional and defaults to ``None``. Reach length matters
    in some domains (rivers, sewer networks) and not in others (link-node water
    distribution models), so override it only where a length exists.

    :attr:`start_distance` and :attr:`end_distance` say where the reach's own
    ends sit in the frame its break points are placed in. They default to
    ``0.0`` and the length, which is right wherever break points are measured
    from the start node; override them where the frame is offset.

    The concrete helper :class:`BasicReach` is provided for the common case
    where all data is already available in memory.

    Examples
    --------
    Minimal subclass, without a length:

    >>> class MyReach(NetworkReach):
    ...     def __init__(self, rid, start_node, end_node):
    ...         self._id = rid
    ...         self._start = start_node
    ...         self._end = end_node
    ...     @property
    ...     def id(self): return self._id
    ...     @property
    ...     def start(self): return self._start
    ...     @property
    ...     def end(self): return self._end
    ...     @property
    ...     def breakpoints(self): return []

    Add a :attr:`length` property on top of that when the domain has one:

    >>> class MyMeasuredReach(MyReach):
    ...     def __init__(self, rid, start_node, end_node, length):
    ...         super().__init__(rid, start_node, end_node)
    ...         self._length = length
    ...     @property
    ...     def length(self): return self._length

    See Also
    --------
    BasicReach : Ready-to-use concrete implementation.
    NetworkNode : Represents the start/end of this reach.
    ReachBreakPoint : Intermediate data points along this reach.
    Network : Assembles a list of NetworkReach objects into a graph.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique string identifier for this reach."""

    @property
    @abstractmethod
    def start(self) -> NetworkNode:
        """Start (upstream) node of this reach."""

    @property
    @abstractmethod
    def end(self) -> NetworkNode:
        """End (downstream) node of this reach."""

    @property
    def length(self) -> float | None:
        """Total length of this reach in network units, or ``None`` if undefined."""
        return None

    @property
    def start_distance(self) -> float:
        """Position of the start node, in the frame :attr:`breakpoints` are placed in.

        Zero for a reach whose break points are measured from its own start.
        Override it where they are not: a MIKE river reach places them at their
        chainage, a coordinate along the whole branch, so a reach can begin
        thousands of metres in - or below zero.
        """
        return 0.0

    @property
    def end_distance(self) -> float | None:
        """Position of the end node, or ``None`` where the length is undefined."""
        length = self.length
        return None if length is None else self.start_distance + length

    @property
    @abstractmethod
    def breakpoints(self) -> list[ReachBreakPoint]:
        """Ordered list of intermediate :class:`ReachBreakPoint` objects (may be empty).

        A break point is keyed by its reach's id, so a reach that has any gets
        its own chain of graph nodes and stays distinct from a parallel reach
        between the same two nodes. A reach with none is a single start-to-end
        edge instead, and two such reaches between one pair of nodes cannot be
        told apart - :class:`Network` refuses them rather than dropping one.
        """

    @property
    def n_breakpoints(self) -> int:
        """Number of break points in the reach."""
        return len(self.breakpoints)


class BasicNode(NetworkNode):
    """Concrete :class:`NetworkNode` for programmatic network construction.

    Parameters
    ----------
    id : str
        Unique node identifier.
    data : pd.DataFrame
        Time-indexed DataFrame with one column per quantity.

    Examples
    --------
    >>> import pandas as pd
    >>> time = pd.date_range("2020", periods=3, freq="h")
    >>> node = BasicNode("junction_1", pd.DataFrame({"WaterLevel": [1.0, 1.1, 1.2]}, index=time))
    """

    def __init__(
        self,
        id: str,
        data: pd.DataFrame,
    ) -> None:
        self._id = id
        self._data = data

    @property
    def id(self) -> str:
        return self._id

    @property
    def data(self) -> pd.DataFrame:
        return self._data


class BasicReach(NetworkReach):
    """Concrete :class:`NetworkReach` for programmatic network construction.

    Parameters
    ----------
    id : str
        Unique reach identifier.
    start : NetworkNode
        Start node.
    end : NetworkNode
        End node.
    length : float, optional
        Reach length, by default None (undefined).
    breakpoints : list[ReachBreakPoint], optional
        Intermediate break points, by default empty.

    Examples
    --------
    >>> reach = BasicReach("reach_1", node_a, node_b, length=250.0)

    Where the domain has no reach length, leave it out:

    >>> reach = BasicReach("pipe_1", node_a, node_b)

    Two of these between the same two nodes - twin pipes, parallel pumps - need
    a break point each, or the graph cannot tell them apart. See
    :attr:`NetworkReach.breakpoints`.
    """

    def __init__(
        self,
        id: str,
        start: NetworkNode,
        end: NetworkNode,
        length: float | None = None,
        breakpoints: list[ReachBreakPoint] | None = None,
    ) -> None:
        self._id = id
        self._start = start
        self._end = end
        self._length = length
        self._breakpoints: list[ReachBreakPoint] = breakpoints or []

    @property
    def id(self) -> str:
        return self._id

    @property
    def start(self) -> NetworkNode:
        return self._start

    @property
    def end(self) -> NetworkNode:
        return self._end

    @property
    def length(self) -> float | None:
        return self._length

    @property
    def breakpoints(self) -> list[ReachBreakPoint]:
        return self._breakpoints
