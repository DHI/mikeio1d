# Design philosophy

* [Easy to use](#easy-to-use)
* [Familiar](#familiar)
* [Easy to install](#easy-to-install)
* [Easy to get started](#easy-to-get-started)
* [Open Source​](#open-source)
* [Easy to collaborate​](#easy-to-collaborate)
* [Reproducible](#reproducible)
* [Easy access to new features](#easy-access-to-new-features)


## Easy to use

Common operations such as reading a file should only need a few lines of code.

Make extensive use of existing standard libraries for scientific computing such as numpy, matplotlib and pandas.


## Familiar

MIKE IO 1D aims to use a syntax familiar to users of scientific computing libraries such as NumPy, Pandas and xarray.

## Easy to install

```bash
$ pip install mikeio1d
```

## Easy to get started
By providing many examples to cut/paste from.

Examples are available in two forms:

* [Unit tests](https://github.com/DHI/mikeio1d/tree/main/tests)
* [Jupyter notebooks](https://nbviewer.jupyter.org/github/DHI/mikeio1d/tree/main/notebooks/)

## Open Source​
MIKE IO 1D is an open source project licensed under the [MIT license](https://github.com/DHI/mikeio1d/blob/main/LICENSE).
The software is provided free of charge with the source code available for inspection and modification.

Contributions are welcome, more details can be found in our [contribution guidelines](https://github.com/DHI/mikeio1d/blob/main/CONTRIBUTING.md).

## Easy to collaborate
By developing MIKE IO 1D on GitHub along with a completely open discussion, we believe that the collaboration between developers and end-users results in a useful library.

## Reproducible
By providing the historical versions of MIKE IO 1D on PyPI it is possible to reproduce the behaviour of an older existing system, based on an older version.

**Install specific version**

```bash
$ pip install mikeio1d==0.4.1
```

## Easy access to new features
Features are being added all the time, by developers at DHI in offices all around the globe as well as external contributors using MIKE IO 1D in their work.
These new features are always available from the [main branch on GitHub](https://github.com/DHI/mikeio1d) and thanks to automated testing, it is always possible to verify that the tests pass before downloading a new development version.

**Install development version**

```bash
$ pip install https://github.com/DHI/mikeio1d/archive/main.zip
```

Note: a required dependency for the development version is [.NET SDK x64](https://dotnet.microsoft.com/en-us/download)
