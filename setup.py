import setuptools
import sysconfig

# Try to download NuGet packages if the download script is present
try:
    from scripts.nuget_retriever import NuGetRetriever

    NuGetRetriever.install()
except Exception as e:
    print("NuGetRetriever failed with an ERROR:")
    print(e)
    print("NuGetRetriever did not succeed: packages are not installed.")

# Try to build DHI.Mike1D.MikeIO C# project
try:
    from scripts.util_builder import UtilBuilder

    UtilBuilder.build_and_install()
except Exception as e:
    print("UtilBuilder failed with an ERROR:")
    print(e)
    print("UtilBuilder did not succeed: packages are not installed.")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mikeio1d",
    version="0.7.0",
    install_requires=[
        "pythonnet>=3.0.0",
        "numpy",
        "pandas>=2.1.0",
        'mikecore; platform_system=="Linux"',
    ],
    python_requires=">=3.9",
    extras_require={
        "dev": [
            "pytest",
            "black",
            "matplotlib",
            "jupyterlab",
            "geopandas",
            "folium",
            "mapclassify",
        ],
        "docs": [
            "quarto-cli",
            "quartodoc==0.7.6",
        ],
        "test": ["pytest", "matplotlib", "pyarrow", "nbformat", "nbconvert", "ipykernel"],
        "all": ["matplotlib", "geopandas"],
    },
    options={
        "bdist_wheel": {
            "plat_name": sysconfig.get_platform().replace("linux-x86_64", "manylinux2010_x86_64")
        }
    },
    author="Gediminas Kirsanskas",
    author_email="geki@dhigroup.com",
    description="A package that uses the DHI MIKE1D .NET libraries to read res1d and xns11 files.",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DHI/mikeio1d",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering",
    ],
)
