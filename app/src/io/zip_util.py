import sys
import traceback
import zipfile

from pathlib import Path


class ZipUtil:
    """
    This class is used to create a zip file of the codebase for deployment.
    """

    def __init__(self):
        self.outfile = None

    def standard_dir_exclusions(self) -> list[str]:
        exclusions = list[str]()
        exclusions.append("__pycache__")
        exclusions.append(".git")
        exclusions.append(".venv")
        exclusions.append("data")
        exclusions.append("htmlcov")
        exclusions.append("tmp")
        return exclusions

    def standard_file_exclusions(self) -> list[str]:
        exclusions = list[str]()
        exclusions.append(".env")
        return exclusions

    def zip_directory(
        self,
        directory: str,
        outfile: str,
        exclude_hidden: bool,
        include_dirs: list[str],
        exclude_dirs: list[str],
        exclude_files: list[str],
    ) -> tuple[bool, int, int]:

        if exclude_dirs is None or len(exclude_dirs) == 0:
            exclude_dirs = self.standard_dir_exclusions()
        if exclude_files is None or len(exclude_files) == 0:
            exclude_files = self.standard_file_exclusions()
        inclusion_count, exclusion_count, verbose = 0, 0, "--verbose" in sys.argv
        try:
            print(f"ZipUtil#zip_directory: {directory} to file: {outfile}")
            dir_path = Path(directory)
            outfile_path = Path(outfile).resolve()
            with zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED) as zip_ref:
                for file_path in sorted(dir_path.rglob("*")):
                    if file_path.is_file():
                        arcname = file_path.relative_to(dir_path)
                        if file_path.resolve() == outfile_path:
                            # never add the zip file being created to itself
                            exclusion_count += 1
                        elif self.is_excluded(
                            arcname, exclude_hidden, include_dirs, exclude_dirs, exclude_files
                        ):
                            exclusion_count += 1
                        else:
                            inclusion_count += 1
                            zip_ref.write(file_path, arcname)
                            if verbose:
                                print(f"ZipUtil#zip_directory included file: {arcname}")
            print(f"ZipUtil#zip_directory created file: {outfile}")
            return (True, inclusion_count, exclusion_count)
        except Exception as e:
            print(f"Error zipping directory: {e}")
            print(traceback.format_exc())
            return (False, inclusion_count, exclusion_count)

    def is_excluded(
        self,
        arcname: Path,
        exclude_hidden: bool = True,
        include_dirs: list[str] = list[str](),
        exclude_dirs: list[str] = list[str](),
        exclude_files: list[str] = list[str](),
    ) -> bool:
        """
        Return True if the given relative file path should be excluded from a zip file.
        Hidden names (beginning with a dot) apply to both the file and its parent dirs;
        if include_dirs is non-empty, only files under one of those dirs are kept, where each
        include_dir is a path relative to the zipped directory (e.g. "src" or "agents/c1");
        exclude_dirs match any parent dir name (e.g. "__pycache__"), or if they contain a slash
        then a path relative to the zipped directory (e.g. "src/dev");
        exclude_files match the file name.
        The exclusions take precedence over include_dirs.
        """
        dir_names = arcname.parts[:-1]
        if include_dirs:
            included = False
            for include_dir in include_dirs:
                include_parts = Path(include_dir).parts
                if dir_names[: len(include_parts)] == include_parts:
                    included = True
            if not included:
                return True
        if exclude_hidden:
            for name in arcname.parts:
                if name.startswith("."):
                    return True
        for exclude_dir in exclude_dirs:
            exclude_parts = Path(exclude_dir).parts
            if len(exclude_parts) == 1:
                if exclude_parts[0] in dir_names:
                    return True
            elif dir_names[: len(exclude_parts)] == exclude_parts:
                return True
        if arcname.name in exclude_files:
            return True
        return False
