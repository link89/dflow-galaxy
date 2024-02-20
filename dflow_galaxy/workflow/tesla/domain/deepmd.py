from dataclasses import dataclass
from typing import Any, List

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice
from dflow_galaxy.core import types


from ai2_kit.domain.deepmd import make_deepmd_task_dirs, make_deepmd_dataset
from ai2_kit.core.util import cmd_with_checkpoint
from ai2_kit.domain import constant


class DeepmdConfig(BaseModel):
    model_num: int = 4
    init_dataset: List[str] = []
    input_template: dict = dict()
    compress_model: bool = False


@dataclass(frozen=True)
class SetupDeepmdTasksArgs:
    input_datasets: types.InputArtifact
    output_dir: types.OutputArtifact


@dataclass(frozen=True)
class AddNewTrainingDatasetArgs:
    label_output_dir: types.InputArtifact
    dataset_dir: types.OutputArtifact


@dataclass(frozen=True)
class RunDeepmdTrainingArgs:
    task_index: types.InputParam[int]

    task_dir: types.InputArtifact
    output_dir: types.OutputArtifact


class SetupDeepmdTaskStep:
    def __init__(self, config: DeepmdConfig, type_map: List[str]):
        self.config = config
        self.type_map = type_map

    def __call__(self, args: SetupDeepmdTasksArgs):
        make_deepmd_task_dirs(input_template=self.config.input_template,
                              model_num=self.config.model_num,
                              train_systems=[args.input_datasets],
                              type_map=self.type_map,
                              base_dir=args.output_dir,
                              isolate_outliers=False,
                              validation_systems=[],
                              outlier_systems=[],
                              outlier_weight=-1.0,
                              dw_input_template=None,
                              )


class RunDeepmdTrainingStep:

    def __init__(self,
                 config: DeepmdConfig,
                 concurrency: int,
                 dp_cmd: str,):
        self.config = config
        self.c = concurrency
        self.dp_cmd = dp_cmd

    def __call__(self, args: RunDeepmdTrainingArgs):
        """generate bash script to run deepmd training commands"""



        script = [
            f"cd {args.task_dir}",
            bash_iter_ls_slice(
                '*/', opt='-d', n=self.c, i=args.task_index, it_var='ITEM',
                script=[

                ]
            ),
        ]
        return script



