from typing import List, Optional, Mapping, Any, Literal
from dataclasses import dataclass

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice
from dflow_galaxy.core import types



class LammpsApp(BaseApp):
    lammps_cmd: str = 'lmp'
    concurrency: int = 5


class LammpsConfig(BaseModel):
    systems: List[str]

    nsteps: int
    no_pbc: bool = False
    timestep: float = 0.0005
    sample_freq: int = 100

    explore_vars: Mapping[str, List[Any]]
    broadcast_vars: Mapping[str, Any] = {}

    template_vars: Mapping[str, Any] = {}
    """
    input_template may provide extra injection points for user to inject custom settings.
    Those value could be set here.

    Those vars can be referenced in the LAMMPS input template as $$VAR_NAME.
    """

    input_template: Optional[str] = None

    plumed_config: Optional[str]

    ensemble: Optional[Literal['nvt', 'nvt-i', 'nvt-a', 'nvt-iso', 'nvt-aniso', 'npt', 'npt-t', 'npt-tri', 'nve', 'csvr']] = None
    fix_statement: Optional[str] = None

    ignore_error: bool = False


@dataclass
class LammpsRuntime:
    ...


@dataclass(frozen=True)
class SetupLammpsTasksArgs:
    model_dir: types.InputArtifact

    work_dir: types.OutputArtifact
    data_dir: types.OutputArtifact


class SetupLammpsTaskFn:
    def __init__(self, config: LammpsConfig):
        self.config = config

    def __call__(self, args: SetupLammpsTasksArgs):
        ...


@dataclass(frozen=True)
class RunLammpsTasksArgs:
    data_dir: types.InputArtifact
    work_dir: types.InputArtifact

    persist_dir: types.OutputArtifact





def lammps_provision(builder: DFlowBuilder, ns: str, /,
                     config: LammpsConfig,
                     executor: ExecutorConfig,
                     lammps_app: LammpsApp,
                     python_app: PythonApp,
                     runtime: LammpsRuntime):
    ...
