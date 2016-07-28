# Stubs for cedit (Python 3.5)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from pathlib import Path
from easysettings import EasySettings

NAME = ...  # type: str
VERSIONSTR = ...  # type: str
SCRIPT = ...  # type: str
SCRIPTDIR = ...  # type: str
OPTIONS = ...  # type: Dict[str, str]
CONFIGFILE = ...  # type: str
settings = ...  # type: EasySettings
USAGESTR = ...  # type: str

def main(argd: Dict) -> int: ...
def build_cmd(
        editor: Path,
        paths: Set[Path],
        as_root: Optional[bool]=False) -> List[str]: ...
def filenames_desc(paths: Set[Path]) -> str: ...
def find_executable(name: Path) -> Path: ...
def get_config_path(
        option: str,
        pathtype: Optional[str]=None,
        defaults: Optional[Sequence[str]]=None) -> Path: ...
def get_editor(as_root=False) -> Path: ...
def get_elevcmd() -> Path: ...
def is_executable(path: Union[str, Path]) -> bool: ...
def needs_root(path: Union[str, OpenPath]) -> bool: ...
def parse_filepaths(filenames: Sequence[str]) -> Set[OpenPath]: ...
def print_err(*args: Any, **kwargs: Any) -> None: ...
def quote_arg(s: str) -> str: ...
def run_exec(cmdlist: Sequence[Union[str, Path]]) -> int: ...
def set_option(args: Sequence[str]) -> bool: ...
def shell_file(paths: Set[Path]) -> bool: ...

class InvalidConfig(ValueError): ...
class InvalidArg(InvalidConfig): ...

class OpenPath(object):
    def __init__(self, *args, **kwargs) -> None: ...
    def __str__(self) -> str: ...
    @staticmethod
    def parse_line_col(s: str) -> Tuple[str, str, str]: ...
    def with_linenum(self) -> str: ...

class PathDesc:
    def __init__(
        self,
        name: str,
        plural: str,
        paths: Optional[Sequence[Path]]=None) -> None: ...

class UserCancelled(KeyboardInterrupt):
    def __init__(self, msg: Optional[str]=None) -> None: ...
