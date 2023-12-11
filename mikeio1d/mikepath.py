import os


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
        mike_bin_path = MikePath.mike_bin_path
        mikeio1d_bin_path = MikePath.mikeio1d_bin_path
        mike_install_path = MikePath.mike_install_path

        syspath.append(mike_bin_path)
        if mikeio1d_bin_path != mike_bin_path:
            syspath.append(mikeio1d_bin_path)

            # Some of the MIKE libraries will need to be resolved by DHI.Mike.Install,
            # so set it up here.
            import clr

            clr.AddReference(
                "DHI.Mike.Install, Version=1.0.0.0, Culture=neutral, PublicKeyToken=c513450b5d0bf0bf"
            )
            from DHI.Mike.Install import MikeImport

            MikeImport.SetupInstallDir(mike_install_path)
