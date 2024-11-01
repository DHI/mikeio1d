"""Module for handling MIKE binary paths."""

import os
import sys
import platform
import pythonnet


class MikePath:
    """Class for handling MIKE binary paths.

    Attributes
    ----------
    mikeio1d_bin_path: string
        Path to binaries contained in MIKE IO 1D Python package.
    mike_install_path: string
        Environment variable MIKE_INSTALL_PATH specifying location of MIKE installation.
    skip_bin_x64: string
        Environment variable specifying not to append 'bin/x64' for binary location.
    bin_x64: string
        String which will be appended to mike_install_path for full location of binaries.
    mike_bin_path: string
        Actual path for MIKE binaries, which is either mikeio1d_bin_path or mike_install_path/bin/x64.

    """

    is_linux = platform.system() == "Linux"

    mikeio1d_bin_path = os.path.join(os.path.dirname(__file__), "bin")

    mikeio1d_bin_extra_path = os.path.join(os.path.dirname(__file__), "bin/DHI.Mike1D.MikeIO")

    mike_install_path = os.environ.get("MIKE_INSTALL_PATH", None)

    skip_bin_x64 = os.environ.get("MIKE_SKIP_BIN_X64", None)
    bin_x64 = os.path.join("bin", "x64") if skip_bin_x64 is None else ""

    mike_bin_path = (
        os.path.join(mike_install_path, bin_x64)
        if mike_install_path is not None
        else mikeio1d_bin_path
    )

    library_patterns = ["DHI.*.dll"]

    @staticmethod
    def setup_mike_installation(syspath):
        """Add MIKE installation bin path and MIKE IO 1D bin path to the given PATH variable.

        Parameters
        ----------
        syspath: list of str
            List of strings defining PATH variable.

        """
        MikePath.update_mike_bin_to_mikepluspy_bin_if_used()

        syspath.append(MikePath.mike_bin_path)
        syspath.append(MikePath.mikeio1d_bin_extra_path)

        if MikePath.is_linux:
            MikePath.setup_mike_installation_linux()

        if MikePath.mikeio1d_bin_path != MikePath.mike_bin_path:
            MikePath.setup_mike_installation_custom(syspath)

    @staticmethod
    def update_mike_bin_to_mikepluspy_bin_if_used():
        """Update the path for MIKE assemblies to the ones used by MIKE+Py package.

        This requires that the MIKE+Py package was already loaded.
        """
        mikepluspy = sys.modules.get("mikeplus")
        if mikepluspy is None:
            return

        import mikeplus

        mikeplus_bin_path = str(mikeplus.MikeImport.ActiveProduct().InstallRoot)
        mikeplus_bin_path = os.path.join(mikeplus_bin_path, MikePath.bin_x64)

        MikePath.mikeio1d_bin_path = mikeplus_bin_path
        MikePath.mike_bin_path = mikeplus_bin_path

    @staticmethod
    def setup_mike_installation_custom(syspath):
        """Add DHI.Mike.Install to the syspath and setup the MIKE installation."""
        # Some of the MIKE libraries will need to be resolved by DHI.Mike.Install,
        # so set it up here.
        import clr

        clr.AddReference(
            "DHI.Mike.Install, Version=1.0.0.0, Culture=neutral, PublicKeyToken=c513450b5d0bf0bf"
        )
        from DHI.Mike.Install import MikeImport

        MikeImport.SetupInstallDir(MikePath.mike_install_path)

    @staticmethod
    def setup_mike_installation_linux():
        """Set up MIKE installation on Linux."""
        # This mikecore import statement is for resolution of MIKE Core native libraries on Linux.
        # Note that setting LD_LIBRARY_PATH in the process has no effect.
        # The mikecore has patchelfed MIKE Core libraries,
        # which helps to resolve them without LD_LIBRARY_PATH.
        # Also it performs ctypes.CDLL statements to load the libraries
        # and initialization of the libraries.
        import mikecore

        runtime_config = os.path.join(
            MikePath.mike_bin_path, "DHI.Mike1D.Application.runtimeconfig.json"
        )
        pythonnet.load("coreclr", runtime_config=runtime_config)
