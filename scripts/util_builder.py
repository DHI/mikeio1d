import os
import shutil
import subprocess


class UtilBuilder:
    """
    Build utility libraries for MIKE IO 1D.
    """

    # Default path
    path_default = '.\\'

    # Directory for utility package source code
    util_dir_name = 'util'

    # Directory where libraries are build
    build_dir_name = r'bin\Release\netstandard2.0'

    # Directory where libraries will be installed
    bin_dir_name = r'mikeio1d\bin'

    # Utility libraries to build and install
    library_names = ['DHI.Mike1D.MikeIO']

    # Files with these extensions copy
    extensions = ['.dll']

    def __init__(self, path=path_default):
        self.path = path

    def build_libraries(self):
        print('  Building utility libraries:')

        for library in self.library_names:
            project_file_name = library + '.csproj'
            project_file_path = os.path.join(self.path, self.util_dir_name, library, project_file_name)

            print(f'    Building project: {project_file_name}\n')

            command = ['dotnet.exe', 'build', '--configuration', 'Release', project_file_path]
            subprocess.run(command)

    def copy_libraries_to_bin(self):
        destination = os.path.join(self.path, self.bin_dir_name)

        print(f'  Copying utility libraries into: {destination}')

        files = self.create_file_list_to_copy()

        for source_file in files:
            source_file_path_stripped = source_file.split('\\')[-1]
            print(f'    Copying file: {source_file_path_stripped}')
            _, file_name = os.path.split(source_file)
            destination_file = os.path.join(destination, file_name)
            shutil.copy2(source_file, destination_file)

    def create_file_list_to_copy(self):
        start_dir = os.path.join(self.path, self.util_dir_name)
        files = []

        for library in self.library_names:
            for extension in self.extensions:
                file_name = library + extension
                file_path = os.path.join(start_dir, library, self.build_dir_name, file_name)
                files.append(file_path)

        return files

    @staticmethod
    def build_and_install():
        """ Builds and installs MIKE IO 1D utilities into mikeio1d/bin folder """
        cwd = os.getcwd()
        path, _ = os.path.split(os.path.join(cwd, __file__))
        path = os.path.normpath(os.path.join(path, '../'))

        util_builder = UtilBuilder(path)
        util_builder.build_libraries()
        util_builder.copy_libraries_to_bin()

        print()
