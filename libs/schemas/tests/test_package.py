import sentio_schemas


def test_package_exposes_its_version() -> None:
    assert sentio_schemas.__version__ == "0.1.0"
