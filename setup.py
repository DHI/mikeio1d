import setuptools

# Try to download NuGet packages if the download script is present
try:
    from scripts.nuget_retriever import NuGetRetriever
    NuGetRetriever.install()
except Exception as e:
    print('NuGetRetriever failed with an ERROR:')
    print(e)
    print("NuGetRetriever did not succeed: packages are not installed.")

# Try to build DHI.Mike1D.MikeIO C# project
try:
    from scripts.util_builder import UtilBuilder
    UtilBuilder.build_and_install()
except Exception as e:
    print('UtilBuilder failed with an ERROR:')
    print(e)
    print("UtilBuilder did not succeed: packages are not installed.")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mikeio1d",
    version="0.4.0",
    install_requires=[
        'pythonnet<=2.5.2; python_version < "3.7.0"',
        'pythonnet>=3.0.0a2; python_version >= "3.7.0"',
        "numpy",
        "pandas",
    ],
    extras_require={
        "dev": [
            "pytest",
            "black",
            "sphinx",
            "sphinx-rtd-theme",
            "matplotlib",
            "jupyterlab",
        ],
        "test": ["pytest", "matplotlib"],
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
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Scientific/Engineering",
    ],
)
