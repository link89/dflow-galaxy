from typing import List, Optional, Mapping, Any, Literal, Tuple
from dataclasses import dataclass

from dflow_galaxy.core.pydantic import BaseModel
from typing import Literal

from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice
from dflow_galaxy.core import types

import pandas as pd


class ModelDeviConfig(BaseModel):
    metric: Literal["max_devi_v",  "min_devi_v",  "avg_devi_v",  "max_devi_f",  "min_devi_f",  "avg_devi_f"] = 'max_devi_f'
    decent: Tuple[float, float]


@dataclass(frozen=True)
class ModelDeviArgs:
    explore_dir: types.InputArtifact
    work_dir: types.OutputArtifact


class RunModelDeviTasksFn:

    def __init__(self, config: ModelDeviConfig):
        self.config = config

    def __call__(self, args: ModelDeviArgs):
        ...


def provision_model_devi(builder: DFlowBuilder, ns: str, /,
                         config: ModelDeviConfig,
                         executor: ExecutorConfig,
                         python_app: PythonApp,
                         ):
    run_task_fn = RunModelDeviTasksFn(config)


