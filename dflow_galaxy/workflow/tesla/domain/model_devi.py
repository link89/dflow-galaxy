from typing import List, Optional, Mapping, Any, Literal, Tuple
from dataclasses import dataclass

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice
from dflow_galaxy.core import types



class ModelDeviConfig(BaseModel):
    decent_f: Tuple[float, float]

