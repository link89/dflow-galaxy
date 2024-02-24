from typing import List, Optional, Mapping, Any, Literal
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import glob
import os

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice, safe_ln, get_ln_cmd
from dflow_galaxy.core import types

from ai2_kit.domain.cp2k import make_cp2k_task_dirs
from ai2_kit.core.artifact import Artifact, ArtifactDict
from ai2_kit.core.util import cmd_with_checkpoint as cmd_cp, list_sample, load_text, dump_text

from dflow import argo_range

from .lib import resolve_artifact

INIT_SYSTEM_DIR = './init-systems'
ITER_SYSTEM_DIR = './iter-systems'


class Cp2kApp(BaseApp):
    cp2k_cmd: str = 'cp2k.popt'
    concurrency: int = 5


class Cp2kConfig(BaseModel):
    init_systems: List[str] = []
    input_template: Optional[str] = None
    template_vars: Mapping[str, Any] = {}

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

        system_files: List[ArtifactDict] = []
        if self.init:
            # handle init systems
            limit = 0  # no limit for init systems
            assert self.config.init_systems, 'init_systems should not be empty for first iteration'
            for k in self.config.init_systems:
                v = deepcopy(self.systems[k])  # avoid side effect
                v.url = os.path.join(INIT_SYSTEM_DIR, k)
                system_files.extend(resolve_artifact(v))
        else:
            # handle iter systems
            system_dirs = glob.glob(f'{ITER_SYSTEM_DIR}/system/*')  # search pattern is defined by model_devi
            for sys_dir in system_dirs:
                sys_dir = Path(sys_dir)
                ancestor = load_text(sys_dir / 'ANCESTOR')
                a_dict = {
                    'url': str(sys_dir / 'decent.xyz'),
                    'format': 'extxyz',
                    'attrs': deepcopy(self.systems[ancestor].attrs),
                }
                system_files.append(a_dict)  # type: ignore

        # TODO: type_map is no longer needed, should be fixed in ai2-kit
        task_dirs = make_cp2k_task_dirs(
            system_files=system_files,
            input_template=self.config.input_template,
            template_vars=self.config.template_vars,
            base_dir=args.work_dir,
            limit=limit,
            # not supported yet
            mode='default',
            wfn_warmup_template=None,
            # deprecated
            type_map=[],
        )
        for task_dir in task_dirs:
            path = os.path.join(task_dir['url'], 'ANCESTOR')
            dump_text(task_dir['attrs']['ancestor'], path)


def provision_cp2k(builder: DFlowBuilder, ns: str, /,
                   config: Cp2kConfig,
                   executor: ExecutorConfig,
                   cp2k_app: Cp2kApp,
                   python_app: PythonApp,

                   init_system_url: str,
                   iter_system_url: str,
                   work_dir_url: str,

                   init: bool,
                   systems: Mapping[str, Artifact],
                   ):
    setup_tasks_fn = SetupCp2kTaskFn(config, systems=systems, init=init)
    setup_tasks_step = builder.make_python_step(setup_tasks_fn, uid=f'{ns}-setup-task',
                                                setup_script=python_app.setup_script,
                                                executor=create_dispatcher(executor, python_app.resource))(
        SetupCp2kTasksArgs(
            init_system_dir=init_system_url,
            iter_system_dir=iter_system_url,
            work_dir=work_dir_url,
        )
    )
    builder.add_step(setup_tasks_step)
