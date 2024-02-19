from typing import List, Mapping, Optional
from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core import dispatcher


class SoftwareConfig(BaseModel):
    executor: str
    resource_plan: dispatcher.ResourcePlan
    setup_script: Optional[str] = None
    container: Optional[str] = None


class GeneralConfig(BaseModel):
    type_map: List[str]
    mass_map: List[str]


class LabelConfig(BaseModel):
    ...


class TrainConfig(BaseModel):
    ...


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
    executors: Mapping[str, dispatcher.ExecutorConfig]
    softwares: Mapping[str, SoftwareConfig]
    datasets: Mapping[str, str]
    workflow: WorkflowConfig

