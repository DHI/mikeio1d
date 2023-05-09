import os
import shutil
import urllib.request
import zipfile
from glob import glob


class NuGetPackageInfo:
    """
    Information about NuGet package to retrieve
    """

    root = 'https://www.nuget.org/api/v2/package/'

    def __init__(self, name, version, path):
        nuget = NuGetRetriever.nuget_dir_name

        self.name = name
        self.version = version
        self.path = path

        self.dir_name = f'{path}/{nuget}/{name}.{version}'
        self.zip_name = f'{path}/{nuget}/{name}.{version}.zip'
        self.link = f'{self.root}{name}/{version}'


class NuGetRetriever:
    """
    Retrieves necessary DHI NuGet packages and installs them into bin folder of MIKE IO 1D.
    """

    # Default path
    path_default = '.\\'

    # Directory where NuGet packages will be downloaded
    nuget_dir_name = 'nuget'

    # Directory where libraries will be installed
    bin_dir_name = r'mikeio1d\bin'

    # Default version of DHI NuGet packages to retrieve
    version_default = '21.0.0'

    # DHI NuGet packages to install
    package_names = [
        'DHI.Chart.Map',
        'DHI.DHIfl',
        'DHI.DFS',
        'DHI.EUM',
        'DHI.PFS',
        'DHI.Projections',
        'DHI.Mike1D.CrossSectionModule',
        'DHI.Mike1D.HDParameterDataAccess',
        'DHI.Mike1D.Generic',
        'DHI.Mike1D.ResultDataAccess',
        'GeoAPI',
        'NetTopologySuite',
    ]

    version_map = {'GeoAPI': '1.7.4', 'NetTopologySuite': '2.0.0'}

    # Builds to include
    include_builds = ['netstandard2.0', 'net45', 'net47', 'win-x64']

    # Files with these extensions copy
    extensions = ['*.dll', '*.pfs', '*.ubg', '*.xml']

    def __init__(self, path=path_default, version=version_default):
        self.path = path
        self.version = version

    def install_packages(self):
        self.create_nuget_dir_if_needed()
        self.generate_package_infos()
        self.download_packages()
        self.extract_packages()
        self.copy_packages_to_bin()

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
        print(f'  Downloading DHI NuGet packages into: {nuget_dir}')

        for info in self.package_infos:
            print(f'    Downloading package: {info.name} {info.version}')
            urllib.request.urlretrieve(info.link, info.zip_name)

    def extract_packages(self):
        version = self.version

        for info in self.package_infos:
            with zipfile.ZipFile(info.zip_name, 'r') as zip_ref:
                zip_ref.extractall(f'./{info.dir_name}')

    def copy_packages_to_bin(self):
        destination = os.path.join(self.path, self.bin_dir_name)

        print(f'  Copying DHI NuGet packages into: {destination}')

        files = self.create_file_list_to_copy()

        for source_file in files:
            source_file_path_stripped = source_file.split(r'\nuget')[1]
            print(f'    Copying file: {source_file_path_stripped}')
            _, file_name = os.path.split(source_file)
            destination_file = os.path.join(destination, file_name)
            shutil.copy2(source_file, destination_file)

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
        for build in self.include_builds:
            if build in file_candidate:
                include_file = True
        return include_file

    @staticmethod
    def install(version=version_default):
        """ Installs NuGet packages into mikeio1d/bin folder """
        cwd = os.getcwd()
        path, _ = os.path.split(os.path.join(cwd, __file__))
        path = os.path.normpath(os.path.join(path, '../'))

        print("Installing DHI NuGet packages:")

        retriever = NuGetRetriever(path, version)
        retriever.install_packages()

        print()
