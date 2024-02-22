from typing import List, Optional, Mapping, Any, Literal
from dataclasses import dataclass

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice
from dflow_galaxy.core import types

from ai2_kit.domain.lammps import make_lammps_task_dirs


class LammpsApp(BaseApp):
    lammps_cmd: str = 'lmp'
    concurrency: int = 5


class LammpsConfig(BaseModel):
    dataset: List[str]

    nsteps: int
    no_pbc: bool = False
    timestep: float = 0.0005
    sample_freq: int = 100

    product_vars: Mapping[str, List[Any]]
    broadcast_vars: Mapping[str, Any] = {}

    template_vars: Mapping[str, Any] = {}
    """
    input_template may provide extra injection points for user to inject custom settings.
    Those value could be set here.

    Those vars can be referenced in the LAMMPS input template as $$VAR_NAME.
    """

    input_template: Optional[str] = None
    plumed_config: Optional[str] = None
    ensemble: Optional[Literal['nvt', 'nvt-i', 'nvt-a', 'nvt-iso', 'nvt-aniso', 'npt', 'npt-t', 'npt-tri', 'nve', 'csvr']] = None
    ignore_error: bool = False


@dataclass(frozen=True)
class SetupLammpsTasksArgs:
    model_dir: types.InputArtifact

    work_dir: types.OutputArtifact
    data_dir: types.OutputArtifact


class SetupLammpsTaskFn:
    def __init__(self, config: LammpsConfig, type_map: List[str], mass_map: List[float]):
        self.config = config
        self.type_map = type_map
        self.mass_map = mass_map


    def __call__(self, args: SetupLammpsTasksArgs):
        # TODO: handle data_files and dp_models



        make_lammps_task_dirs(
            combination_vars=self.config.product_vars,
            broadcast_vars=self.config.broadcast_vars,
            data_files=[], # TODO
            dp_models={}, # TODO
            n_steps=self.config.nsteps,
            timestep=self.config.timestep,
            sample_freq=self.config.sample_freq,
            no_pbc=self.config.no_pbc,
            ensemble=self.config.ensemble,
            input_template=self.config.input_template,
            plumed_config=self.config.plumed_config,
            extra_template_vars=self.config.template_vars,
            type_map=self.type_map,
            mass_map=self.mass_map,

            work_dir='', # TODO

            # TODO: support more feature in the future
            mode='default',
            type_alias={},
            dp_modifier=None,
            dp_sel_type=None,
            preset_template='default',
            n_wise=0,
            fix_statement=None,
            ai2_kit_cmd='python -m ai2_kit.main',
        )


@dataclass(frozen=True)
class RunLammpsTasksArgs:
    slice_idx: types.InputParam[types.SliceIndex]
    data_dir: types.InputArtifact
    work_dir: types.InputArtifact
    persist_dir: types.OutputArtifact


class RunLammpsTasksFn:
    def __init__(self, config: LammpsConfig):
        self.config = config

    def __call__(self, args: RunLammpsTasksArgs):
        ...


def lammps_provision(builder: DFlowBuilder, ns: str, /,
                     config: LammpsConfig,
                     executor: ExecutorConfig,
                     lammps_app: LammpsApp,
                     python_app: PythonApp,

                     dataset_url: str,
                     work_dir_url: str,
                     type_map: List[str],
                     mass_map: List[float],
                     ):
    ...
