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