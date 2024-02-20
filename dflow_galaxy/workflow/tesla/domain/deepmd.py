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
    input_template: dict = {}
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
            f"pushd {args.task_dir}",
            bash_iter_ls_slice(
                '*/', opt='-d', n=self.c, i=args.task_index, it_var='ITEM',
                script=[
                    '# dp train',
                    'pushd $ITEM',
                    'mv out/* . || true  # recover from previous run',
                    self._build_dp_train_script(),
                    '',
                    '# move artifacts to output dir',
                    f'OUT_DIR={args.output_dir}/$ITEM/out/',
                    f'mkdir -p $OUT_DIR',
                    f'mv *.done $OUT_DIR',
                    f'mv {constant.DP_FROZEN_MODEL} $OUT_DIR',
                    f'mv {constant.DP_ORIGINAL_MODEL} $OUT_DIR || true',
                    'popd',
                ]
            ),
            'popd',
        ]
        return script

    def _build_dp_train_script(self):
        train_cmd = f'{self.dp_cmd} train {constant.DP_INPUT_FILE}'
        # TODO: handle restart, initialize from previous model, support pretrain model
        script = [
            cmd_with_checkpoint(train_cmd, 'dp-train.done', False),
            f'{self.dp_cmd} freeze -o {constant.DP_ORIGINAL_MODEL}',
        ]
        # compress (optional) and frozen model
        if self.config.compress_model:
            script.append(f'{self.dp_cmd} compress -i {constant.DP_ORIGINAL_MODEL} -o {constant.DP_FROZEN_MODEL}')
        else:
            script.append(f'mv {constant.DP_ORIGINAL_MODEL} {constant.DP_FROZEN_MODEL}')
        return '\n'.join(script)
