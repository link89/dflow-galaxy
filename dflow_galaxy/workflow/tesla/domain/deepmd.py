from dataclasses import dataclass
from typing import List

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core import types


from ai2_kit.domain.deepmd import make_deepmd_task_dirs, make_deepmd_dataset
from ai2_kit.core.util import list_split


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

    r_kv: types.InputArtifact
    w_kv: types.OutputArtifact


def make_add_new_training_dataset_step(config: DeepmdConfig,
                                       type_map: List[str],
                                       ):
    def add_new_training_dataset(args: AddNewTrainingDatasetArgs):
        ...

    return add_new_training_dataset


def make_setup_deepmd_tasks_step(config: DeepmdConfig,
                                 type_map: List[str],
                                 ):
    def setup_deepmd_tasks(args: SetupDeepmdTasksArgs):
        make_deepmd_task_dirs(input_template=config.input_template,
                              model_num=config.model_num,
                              train_systems=[args.input_datasets],
                              type_map=type_map,
                              base_dir=args.output_dir,
                              isolate_outliers=False,
                              validation_systems=[],
                              outlier_systems=[],
                              outlier_weight=-1.0,
                              dw_input_template=None,
                              )
    return setup_deepmd_tasks


def make_run_deepmd_training_step(config: DeepmdConfig,
                                  concurrency: int,
                                  ):

    def run_deepmd_training(args: RunDeepmdTrainingArgs):
        import os


        task_dir = sorted(os.listdir(args.task_dir))[args.task_index]










    return run_deepmd_training




def add_deepmd_steps(dflow_builder: DFlowBuilder, config: DeepmdConfig, type_map: List[str]):

    ...
