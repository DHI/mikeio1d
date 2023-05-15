import os


def setup_mike_installation(syspath):
    """
    Adds MIKE installation bin path and MIKE IO 1D bin path to the
    given PATH variable.

    Parameters
    ----------
    syspath: list of str
        List of strings defining PATH variable.
    """
    # It could be possible to try to use DHI.Mike.Install instead
    #   clr.AddReference("DHI.Mike.Install, Version=1.0.0.0, Culture=neutral, PublicKeyToken=c513450b5d0bf0bf")
    #   from DHI.Mike.Install import MikeImport, MikeProducts
    #   MikeImport.SetupLatest(MikeProducts.MikePlus)
    syspath.append(mike_bin_path)
    if mikeio1d_bin_path != mike_bin_path:
        syspath.append(mikeio1d_bin_path)


mikeio1d_bin_path = os.path.join(os.path.dirname(__file__), "bin")

mike_install_path = os.environ.get("MIKE_INSTALL_PATH", None)

skip_bin_x64 = os.environ.get("SKIP_BIN_X64", None)
bin_x64 = r"bin\x64" if skip_bin_x64 is None else ""

mike_bin_path = (
    os.path.join(mike_install_path, bin_x64)
    if mike_install_path is not None
    else mikeio1d_bin_path
)

library_patterns = ["DHI.*.dll"]
