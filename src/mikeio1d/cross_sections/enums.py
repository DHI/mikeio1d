"""Enums for cross sections."""

from __future__ import annotations

from enum import IntEnum


class ResistanceType(IntEnum):
    """The type of resistance used in the cross section.

    This is a simple wrapper of DHI.Mike1D.Generic.ResistanceFormulation
    """

    RELATIVE = 0
    """
    Relative factor. The factor is relative to the globally provided resistance formulation and number.
    """
    MANNINGS_N = 1
    """
    Manning's n.
    """
    MANNINGS_M = 2
    """
    Manning's M.
    """
    CHEZY = 3
    """
    Chezy.
    """
    DARCY_WEISBACH = 4
    """
    Darcy-Weisbach resistance.

    Note that Darcy-Weisbach resistance values are converted to Chezy resistance numbers while processing, 
    so for a Darcy-Weisbach formulation the raw resistance values are Darcy-Weisbach, while the processed 
    ones are Chezy.
    """
    COLEBROOK_WHITE = 5
    """
    Colebrook White. Only used with circular CrossSections
    """
    HAZEN_WILLIAMS = 6
    """
    Hazen Williams.
    """
    MANNINGS_M_RELATIVE = 66
    """
    Manning's M, relative, meaning that raw/processed resistance numbers are relative to the local manning
    number.
    """


class ResistanceDistribution(IntEnum):
    """The type of resistance distribution used in the cross section.

    This is a simple wrapper of DHI.Mike1D.Generic.ResistanceDistribution.
    """

    UNIFORM = 0
    """
    Uniform within the regular channel and vegetation parts, resp. (ie, 2 values). Resistance values are 
    part of processed data.
    """
    ZONES = 1
    """
    High/low flow zones along the cross section profile, defined by low flow markers (4, LeftLowFlowBank 
    and 5, RightLowFlowBank). Resistance values are part of processed data.
    """
    DISTRIBUTED = 2
    """
    Fully user-distributed along cross section profile. Resistance values are part of processed data.
    """
    CONSTANT = 16
    """
    Resistance value is constant for all water depths. Processed resistance values are not used.
    """
    EXPONENT_VARYING = 17
    """
    Resistance is depth dependent with an exponential variation between top and bottom. 
    Processed resistance values are not used.
    """


class RadiusType(IntEnum):
    """The type of hydraulic radius to use in the cross section.

    This is a simple wrapper of DHI.Mike1D.Generic.RadiusType.
    """

    RESISTANCE_RADIUS = 0
    """
    Resistance radius.
    """
    HYDRAULIC_RADIUS_EFFECTIVE_AREA = 1
    """
    Hydraulic radius, effective area.
    """
    HYDRAULIC_RADIUS_TOTAL_AREA = 2
    """
    Hydraulic radius, total area.
    """


class ProcessLevelsMethod(IntEnum):
    """How to generate processing levels.

    This is a simple wrapper of DHI.Mike1D.Generic.ProcessingOption
    """

    AUTOMATIC_LEVELS = 0
    """
    Use the built-in algorithm to find appropriate processed levels.
    """
    EQUIDISTANT_LEVELS = 1
    """
    Equidistant processed levels between a given min/max pair.
    """
    USER_DEFINED_LEVELS = 2
    """
    Processed levels are user-defined.
    """
