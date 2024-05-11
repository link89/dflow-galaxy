from typing import List, Optional, Mapping, Any, Literal
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
import glob
import os

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow_builder import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice, safe_ln, bash_ln_cmd, bash_inspect_dir, inspect_dir
from dflow_galaxy.core import types

from ai2_kit.domain.cp2k import make_cp2k_task_dirs
from ai2_kit.core.artifact import Artifact, ArtifactDict
from ai2_kit.core.util import cmd_with_checkpoint as cmd_cp, list_sample, load_text, dump_text, ensure_dir

from dflow import argo_range


@dataclass(frozen=True)
class RunReweightingTaskArgs:
    baseline_system_dir: types.InputArtifact
    baseline_colvar_file: types.InputArtifact
    baseline_model_file : Optional[types.InputArtifact]
    target_model_file: types.InputArtifact

    output_dir: types.OutputArtifact


class RunReweightingTask:

    def __init__(self):
        ...

    def __call__(self, args: RunReweightingTaskArgs):
        ...
