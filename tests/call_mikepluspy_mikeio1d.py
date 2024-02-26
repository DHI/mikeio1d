import sys


def test_mikeio1d_and_mikepluspy_coexistence(test_file_path):
    # This test cannot run on a GitHub pipeline, because currently there is no way
    # to have MIKE+ installation on a virtual machine there.
    try:
        import mikeplus
    except:
        return

    from mikeplus.engines import Engine1D
    from mikeio1d import Res1D

    res1d = Res1D(test_file_path, result_reader_type="copier")

    df = res1d.read()


if __name__ == "__main__":
    test_mikeio1d_and_mikepluspy_coexistence(sys.argv[1])
