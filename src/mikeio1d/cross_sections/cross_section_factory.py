"""CrossSectionFactory class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable
    import pandas as pd


from DHI.Mike1D.Generic import ZLocation
from DHI.Mike1D.Generic import RadiusType
from DHI.Mike1D.Generic import ResistanceDistribution
from DHI.Mike1D.Generic import ResistanceFormulation
from DHI.Mike1D.CrossSectionModule import CrossSectionFactory as M1DCrossSectionFactory
from DHI.Mike1D.CrossSectionModule import CrossSectionPoint
from DHI.Mike1D.CrossSectionModule import CrossSectionPointList
from DHI.Mike1D.CrossSectionModule import FlowResistance


class CrossSectionFactory:
    """Factory for creating cross sections."""

    @staticmethod
    def validate(m1d_cross_section):
        """Validate a cross section."""
        diagnostics = m1d_cross_section.Validate()
        if diagnostics.ErrorCountRecursive > 0:
            message = diagnostics.Errors.Count + " errors in cross section."
            message += "\n" + diagnostics.Errors
            raise ValueError(message)

    @staticmethod
    def create_open_from_xz_data(
        x: Iterable[float],
        z: Iterable[float],
        location_id: str,
        chainage: float,
        topo_id: str,
        default_markers: bool = True,
    ):
        """Create an open cross section from x and z data."""
        builder = M1DCrossSectionFactory()

        builder.BuildOpen("")
        builder.SetLocation(ZLocation(location_id, chainage))

        points = CrossSectionPointList()
        for point in zip(x, z):
            point = CrossSectionPoint(*point)
            points.Add(point)
        builder.SetRawPoints(points)

        if default_markers:
            builder.SetDefaultMarkers()
        flow_resistance = FlowResistance()
        flow_resistance.ResistanceDistribution = ResistanceDistribution.Uniform
        flow_resistance.ResistanceValue = 1
        flow_resistance.Formulation = ResistanceFormulation.Relative
        builder.SetFlowResistance(flow_resistance)

        builder.SetRadiusType(RadiusType.ResistanceRadius)

        xs = builder.GetCrossSection()
        xs.TopoID = topo_id
        xs.BaseCrossSection.CalculateProcessedData()

        CrossSectionFactory.validate(xs)

        return xs
