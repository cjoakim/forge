import zipfile

from pathlib import Path

from src.io.zip_util import ZipUtil

# pytest -v tests/test_zip_util.py


def create_test_tree(root: Path) -> Path:
    src = root / "src"
    for relpath in [
        "a.py",
        ".env",
        "skip.txt",
        "pkg/b.py",
        "pkg/.hidden.py",
        "pkg/__pycache__/b.cpython-314.pyc",
        ".git/config",
        "other/c.py",
    ]:
        file_path = src / relpath
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(relpath)
    return src


def zipped_names(outfile: Path) -> list[str]:
    with zipfile.ZipFile(outfile) as zip_ref:
        return sorted(zip_ref.namelist())


def test_is_excluded():
    zu = ZipUtil()
    assert zu.is_excluded(Path(".env"), True, [], [], []) is True
    assert zu.is_excluded(Path(".env"), False, [], [], []) is False
    assert zu.is_excluded(Path(".git/config"), True, [], [], []) is True
    assert zu.is_excluded(Path("pkg/__pycache__/x.pyc"), False, [], ["__pycache__"], []) is True
    assert zu.is_excluded(Path("pkg/b.py"), True, [], ["__pycache__"], []) is False
    assert zu.is_excluded(Path("pkg/b.py"), True, [], [], ["b.py"]) is True
    assert zu.is_excluded(Path("pkg/b.py"), True, [], ["b.py"], []) is False
    assert zu.is_excluded(Path("pkg/b.py"), True, ["pkg"], [], []) is False
    assert zu.is_excluded(Path("a.py"), True, ["pkg"], [], []) is True
    assert zu.is_excluded(Path("other/c.py"), True, ["pkg"], [], []) is True
    assert zu.is_excluded(Path("other/pkg/c.py"), True, ["pkg"], [], []) is True
    assert zu.is_excluded(Path("other/pkg/c.py"), True, ["other/pkg"], [], []) is False
    assert zu.is_excluded(Path("other/c.py"), True, ["other/pkg"], [], []) is True
    assert zu.is_excluded(Path("pkg/b.py"), True, ["pkg/"], [], []) is False
    assert (
        zu.is_excluded(Path("src/os/__pycache__/x.pyc"), True, ["src"], ["__pycache__"], []) is True
    )
    assert zu.is_excluded(Path("src/os/readme.md"), True, ["src"], [], ["readme.md"]) is True
    assert zu.is_excluded(Path("src/dev/x.py"), True, ["src"], ["src/dev"], []) is True
    assert zu.is_excluded(Path("src/os/dev/x.py"), True, ["src"], ["src/dev"], []) is False
    assert zu.is_excluded(Path("src/os/x.py"), True, ["src"], ["src/dev"], []) is False
    assert zu.is_excluded(Path("pkg/__pycache__/x.pyc"), True, ["pkg"], ["__pycache__"], []) is True


def test_zip_directory_defaults(tmp_path):
    src = create_test_tree(tmp_path)
    outfile = tmp_path / "src.zip"
    result = ZipUtil().zip_directory(str(src), str(outfile), True, [], None, None)
    assert result == (True, 4, 4)
    assert zipped_names(outfile) == ["a.py", "other/c.py", "pkg/b.py", "skip.txt"]


def test_zip_directory_with_exclusions(tmp_path):
    src = create_test_tree(tmp_path)
    outfile = tmp_path / "src.zip"
    result = ZipUtil().zip_directory(
        str(src),
        str(outfile),
        exclude_hidden=False,
        include_dirs=[],
        exclude_dirs=["other", "__pycache__"],
        exclude_files=["skip.txt"],
    )
    assert result == (True, 5, 3)
    assert zipped_names(outfile) == [".env", ".git/config", "a.py", "pkg/.hidden.py", "pkg/b.py"]


def test_zip_directory_with_include_dirs(tmp_path):
    src = create_test_tree(tmp_path)
    outfile = tmp_path / "src.zip"
    result = ZipUtil().zip_directory(str(src), str(outfile), True, ["pkg"], None, None)
    assert result == (True, 1, 7)
    assert zipped_names(outfile) == ["pkg/b.py"]


def test_zip_directory_skips_its_own_outfile(tmp_path):
    src = create_test_tree(tmp_path)
    outfile = src / "self.zip"
    result = ZipUtil().zip_directory(str(src), str(outfile), True, [], None, None)
    assert result == (True, 4, 5)
    assert zipped_names(outfile) == ["a.py", "other/c.py", "pkg/b.py", "skip.txt"]
