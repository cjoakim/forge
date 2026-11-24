from src.util.pyproject_parser import PyprojectParser

# pytest -v tests/test_pyproject_parser.py


def test_all():
    pp = PyprojectParser()
    pp.parse()
    print(f"name: {pp.get_name()}")
    print(f"version: {pp.get_version()}")
    print(f"description: {pp.get_description()}")
    print(f"dependencies: {pp.get_dependencies()}")
    print(f"dependency names: {pp.get_dependency_names()}")

    assert pp.get_name() == "forge-app"
    assert pp.get_version() == "1.0.0"
    assert pp.get_description() == "Forge Accelerator primary client application"
    dep_names = pp.get_dependency_names()
    # for name in sorted(dep_names):
    #     print(f"assert '{name}' in dep_names")
    assert len(dep_names) > 15 and len(dep_names) < 30

    assert "azure-identity" in dep_names
    assert "azure-search-documents" in dep_names
    assert "azure-storage-blob" in dep_names
