import os
import platform
import pythonnet


class MikePath:
    """
    Class for handling MIKE binary paths.

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
        """
        Adds MIKE installation bin path and MIKE IO 1D bin path to the
        given PATH variable.

        Parameters
        ----------
        syspath: list of str
            List of strings defining PATH variable.
        """
        syspath.append(MikePath.mike_bin_path)

        if MikePath.is_linux:
            MikePath.setup_mike_installation_linux()

        if MikePath.mikeio1d_bin_path != MikePath.mike_bin_path:
            MikePath.setup_mike_installation_custom(syspath)

    @staticmethod
    def setup_mike_installation_custom(syspath):
        syspath.append(MikePath.mikeio1d_bin_path)

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
