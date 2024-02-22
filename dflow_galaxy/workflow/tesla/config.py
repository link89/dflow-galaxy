from typing import List, Mapping, Optional
from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core import dispatcher
from ai2_kit.core.artifact import Artifact

from .domain import deepmd, lammps, model_devi, cp2k


class GeneralConfig(BaseModel):
    type_map: List[str]
    mass_map: List[str]
    max_iters: int = 1


class AppsConfig(BaseModel):
    python: dispatcher.PythonApp
    deepmd: Optional['deepmd.DeepmdApp'] = None
    lammps: Optional['lammps.LammpsApp'] = None
    cp2k: Optional['cp2k.Cp2kContext'] = None


class Orchestration(BaseModel):
    deepmd: Optional[str] = None
    lammps: Optional[str] = None
    model_devi: Optional[str] = None
    cp2k: Optional[str] = None


class TeslaExecutorConfig(dispatcher.ExecutorConfig):
    apps: AppsConfig


class LabelConfig(BaseModel):
    ...


class TrainConfig(BaseModel):
    deepmd: deepmd.DeepmdConfig


class ExploreConfig(BaseModel):
    lammps: lammps.LammpsConfig


class ScreenConfig(BaseModel):
    model_devi: model_devi.ModelDeviConfig


class WorkflowConfig(BaseModel):
    general: GeneralConfig
    label: LabelConfig
    train: TrainConfig
    explore: ExploreConfig
    screen: ScreenConfig


class TeslaConfig(BaseModel):
    executors: Mapping[str, TeslaExecutorConfig]
    orchestration: Orchestration
    datasets: Mapping[str, Artifact]
    workflow: WorkflowConfig
