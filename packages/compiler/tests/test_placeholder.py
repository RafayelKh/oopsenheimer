from radcraft_compiler import __version__


def test_compiler_package_imports() -> None:
    assert __version__ == "0.0.0"
