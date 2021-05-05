import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mikeio1d",
    version="0.1.0",
    install_requires=[
        "pythonnet",
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
    author="Henrik Andersson",
    author_email="jan@dhigroup.com",
    description="A package that uses the DHI MIKE1D .NET libraries to read res1d and xns11 files.",
    platform="windows_x64",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Scientific/Engineering",
    ],
)
