import sys

import pytest

if __name__ == "__main__":

    sys.exit(pytest.main(["--cov-report=xml", "--cov=.", "--doctest-modules"]))
