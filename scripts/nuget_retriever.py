"""Module retrieving MIKE 1D nuget packages for runnig MIKE IO 1D."""

import os
import shutil
import urllib.request
import zipfile
import platform

from glob import glob
from pathlib import Path


class NuGetPackageInfo:
    """Information about NuGet package to retrieve."""

    root = "https://www.nuget.org/api/v2/package/"

    def __init__(self, name, version, path):
        nuget = NuGetRetriever.nuget_dir_name

        self.name = name
        self.version = version
        self.path = path

        self.dir_name = f"{path}/{nuget}/{name}.{version}"
        self.zip_name = f"{path}/{nuget}/{name}.{version}.zip"
        self.link = f"{self.root}{name}/{version}"


class NuGetRetriever:
    """Retrieves necessary DHI NuGet packages and installs them into bin folder of MIKE IO 1D."""

    # Default path
    path_default = f".{os.sep}"

    # Directory where NuGet packages will be downloaded
    nuget_dir_name = "nuget"

    # Directory where libraries will be installed
    bin_dir_name = os.path.join("mikeio1d", "bin")

    # Default version of DHI NuGet packages to retrieve
    version_default = "23.0.3"

    # DHI NuGet packages to install
    package_names = [
        "DHI.Chart.Map",
        "DHI.DHIfl",
        "DHI.DFS",
        "DHI.EUM",
        "DHI.PFS",
        "DHI.Projections",
        "DHI.corlib",
        "DHI.Mike1D.CrossSectionModule",
        "DHI.Mike1D.HDParameterDataAccess",
        "DHI.Mike1D.Generic",
        "DHI.Mike1D.ResultDataAccess",
        "NetTopologySuite",
    ]

    package_names_linux = [
        "DHI.MikeCore.Linux.rhel7",
    ]

    version_map = {
        "DHI.corlib": "1.0.0",
        "NetTopologySuite": "2.0.0",
        "DHI.MikeCore.Linux.rhel7": "20.0.0",
    }

    # Builds to include
    include_builds = {
        "Windows": ["netstandard2.0", "net45", "net47", "win-x64"],
        "Linux": ["netstandard2.0", "linux-x64"],
    }

    # Files with these extensions copy
    extensions = ["*.dll", "*.pfs", "*.ubg", "*.xml", "*.so", "*.so.5"]

    def __init__(self, path=path_default, version=version_default):
        self.path = path
        self.version = version

    def install_packages(self):
        self.refine_package_names_list()
        self.create_nuget_dir_if_needed()
        self.generate_package_infos()
        self.download_packages()
        self.extract_packages()
        self.copy_packages_to_bin()

    def refine_package_names_list(self):
        is_linux = platform.system() == "Linux"
        if is_linux:
            self.package_names += self.package_names_linux

    def create_nuget_dir_if_needed(self):
        path = os.path.join(self.path, self.nuget_dir_name)
        if not os.path.exists(path):
            os.mkdir(path)

    def generate_package_infos(self):
        path = self.path
        package_infos = []

        for package_name in self.package_names:
            version = self.version_map.get(package_name, self.version)
            package_info = NuGetPackageInfo(package_name, version, path)
            package_infos.append(package_info)

        self.package_infos = package_infos

    def download_packages(self):
        nuget_dir = os.path.join(self.path, self.nuget_dir_name)
        print(f"  Downloading DHI NuGet packages into: {nuget_dir}")

        for info in self.package_infos:
            print(f"    Downloading package: {info.name} {info.version}")
            urllib.request.urlretrieve(info.link, info.zip_name)

    def extract_packages(self):
        version = self.version

        for info in self.package_infos:
            with zipfile.ZipFile(info.zip_name, "r") as zip_ref:
                extract_dir = os.path.join(".", info.dir_name)
                zip_ref.extractall(extract_dir)

    def copy_packages_to_bin(self):
        destination = os.path.join(self.path, self.bin_dir_name)

        print(f"  Copying DHI NuGet packages into: {destination}")

        files = self.create_file_list_to_copy()

        for source_file in files:
            source_file_path_stripped = self.strip_source_file_path(source_file)
            print(f"    Copying file: {source_file_path_stripped}")
            _, file_name = os.path.split(source_file)
            destination_file = os.path.join(destination, file_name)
            shutil.copy2(source_file, destination_file)

    def strip_source_file_path(self, file_path):
        path = Path(file_path)
        path_stripped = path.parts[-1]
        for path_part in reversed(path.parts):
            if path_part == path_stripped:
                continue
            if path_part == "nuget":
                break
            path_stripped = os.path.join(path_part, path_stripped)
        return path_stripped

    def create_file_list_to_copy(self):
        start_dir = os.path.join(self.path, self.nuget_dir_name)
        extensions = self.extensions
        files = []

        for directory, _, _ in os.walk(start_dir):
            for extension in extensions:
                file_candidates = glob(os.path.join(directory, extension))

                for file_candidate in file_candidates:
                    if not self.check_file_candidate(file_candidate):
                        continue

                    files.append(file_candidate)

        return files

    def check_file_candidate(self, file_candidate):
        include_file = False
        builds = self.include_builds[platform.system()]
        for build in builds:
            if build in file_candidate:
                include_file = True
        return include_file

    @staticmethod
    def install(version=version_default):
        """Installs NuGet packages into mikeio1d/bin folder."""
        cwd = os.getcwd()
        path, _ = os.path.split(os.path.join(cwd, __file__))
        path = os.path.normpath(os.path.join(path, ".."))

        print("Installing DHI NuGet packages:")

        retriever = NuGetRetriever(path, version)
        retriever.install_packages()

        print()
