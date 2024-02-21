from typing import List, Mapping, Optional
from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core import dispatcher

from .domain import (
    deepmd,
    lammps,
    cp2k,
)


class GeneralConfig(BaseModel):
    type_map: List[str]
    mass_map: List[str]
    max_iter: int = 1


class AppsConfig(BaseModel):
    python: dispatcher.PythonApp
    deepmd: Optional['deepmd.DeepmdApp'] = None
    lammps: Optional['lammps.LammpsContext'] = None
    cp2k: Optional['cp2k.Cp2kContext'] = None


class Orchestration(BaseModel):
    deepmd: Optional[str] = None
    lammps: Optional[str] = None
    cp2k: Optional[str] = None


class TeslaExecutorConfig(dispatcher.ExecutorConfig):
    apps: AppsConfig


class LabelConfig(BaseModel):
    ...


class TrainConfig(BaseModel):
    deepmd: deepmd.DeepmdConfig


class ExploreConfig(BaseModel):
    ...


class ScreenConfig(BaseModel):
    ...


class WorkflowConfig(BaseModel):
    general: GeneralConfig
    label: LabelConfig
    train: TrainConfig
    explore: ExploreConfig
    screen: ScreenConfig


class TeslaConfig(BaseModel):
    executors: Mapping[str, TeslaExecutorConfig]
    orchestration: Orchestration
    datasets: Mapping[str, str]
    workflow: WorkflowConfig

