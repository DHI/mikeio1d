from util_builder import UtilBuilder
from nuget_retriever import NuGetRetriever

def install_nuget_packages():
    try:
       NuGetRetriever.install()
    except Exception as e:
        print("NuGetRetriever failed with an ERROR:")
        print("NuGetRetriever did not succeed: packages are not installed.")
        raise e
        
def build_and_install_mikeio_util():
    import os
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.normpath(os.path.join(scripts_dir, ".."))
    util_dir = os.path.join(repo_root, "util")
    if not os.path.isdir(util_dir):
        print("  Skipping utility build: 'util/' directory not found (building from sdist).")
        return
    try:
        UtilBuilder.build_and_install()
    except Exception as e:
        print("UtilBuilder failed with an ERROR:")
        print("UtilBuilder did not succeed: packages are not installed.")
        raise e
    
def main():
    install_nuget_packages()
    build_and_install_mikeio_util()

if __name__ == "__main__":
    main()