
from typing import List, Optional, Mapping, Any, Literal
from dataclasses import dataclass

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice
from dflow_galaxy.core import types


class Cp2kContext(BaseApp):
    cp2k_cmd: str = 'cp2k.popt'
    concurrency: int = 5


class Cp2kConfig(BaseModel):
    input_template: str