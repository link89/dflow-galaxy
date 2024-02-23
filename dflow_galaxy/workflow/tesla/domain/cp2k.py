from typing import List, Optional, Mapping, Any, Literal
from dataclasses import dataclass
from copy import deepcopy
import glob
import os

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice, safe_ln, get_ln_cmd
from dflow_galaxy.core import types

from ai2_kit.domain.lammps import make_lammps_task_dirs
from ai2_kit.domain.constant import DP_FROZEN_MODEL
from ai2_kit.core.artifact import Artifact
from ai2_kit.core.util import cmd_with_checkpoint as cmd_cp

from dflow import argo_range

from .lib import resolve_artifact


class Cp2kContext(BaseApp):
    cp2k_cmd: str = 'cp2k.popt'
    concurrency: int = 5


class Cp2kConfig(BaseModel):
    init_systems: List[str]
    input_template: str

    limit: int = 50
    limit_method: Literal['even', 'random', 'truncate'] = 'even'


@dataclass(frozen=True)
class SetupCp2kTasksArgs:
    init_system_dir: types.InputArtifact
    iter_system_dir: types.InputArtifact
    work_dir: types.OutputArtifact


class SetupCp2kTaskFn:

    def __init__(self, config: Cp2kConfig):
        self.config = config

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        pass