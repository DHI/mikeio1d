from mikeio1d import mikenet


def test_load_mike1d_generic():
    mikenet.load_Mike1D_Generic()
    quantity = mikenet.Mike1D_Generic.Quantity()


def test_load_projections():
    mikenet.load("DHI.Projections")
    map_projection = mikenet.Projections.MapProjection(
        'PROJCS["UTM-33",GEOGCS["Unused",DATUM["UTM Projections",SPHEROID["WGS 1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000],PARAMETER["False_Northing",0],PARAMETER["Central_Meridian",15],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0],UNIT["Meter",1]]'
    )


def test_load_all():
    mikenet.load_all()
    result_data = mikenet.PFS.PFSBuilder()


def test_libraries_loaded_to_clr():
    # Libraries already loaded to CLR by mikeio1d.__init__.py
    import System
    import System.Runtime
    import System.Runtime.InteropServices
    import DHI.Generic.MikeZero.DFS
    import DHI.Generic.MikeZero
    import DHI.Mike1D.Generic
    import DHI.Mike1D.ResultDataAccess
    import DHI.Mike1D.CrossSectionModule
    import DHI.Mike1D.MikeIO

    # Libraries loaded inside test_mikenet.py
    import DHI.PFS
    import DHI.Projections
