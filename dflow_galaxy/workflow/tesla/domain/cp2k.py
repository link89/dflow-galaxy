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

from ai2_kit.domain.cp2k import make_cp2k_task_dirs
from ai2_kit.core.artifact import Artifact, ArtifactDict
from ai2_kit.core.util import cmd_with_checkpoint as cmd_cp, list_sample

from dflow import argo_range

from .lib import resolve_artifact

INIT_SYSTEM_DIR = './init-systems'
ITER_SYSTEM_DIR = './iter-systems'


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

    def __init__(self, config: Cp2kConfig, systems: Mapping[str, Artifact], init: bool):
        self.config = config
        self.init = init
        self.systems = systems

    def __call__(self, args: SetupCp2kTasksArgs):
        safe_ln(args.init_system_dir, INIT_SYSTEM_DIR)
        safe_ln(args.iter_system_dir, ITER_SYSTEM_DIR)

        limit = self.config.limit

        data_files: List[ArtifactDict] = []
        if self.init:
            # handle init systems
            limit = 0  # no limit for init systems
            assert self.config.init_systems, 'init_systems should not be empty for first iteration'
            for k in self.config.init_systems:
                v = deepcopy(self.systems[k])  # avoid side effect
                v.url = os.path.join(INIT_SYSTEM_DIR, k)
                data_files.extend(resolve_artifact(v))
        else:
            # handle iter systems
            ...