from dataclasses import dataclass
from typing import List

from ai2_kit.domain.deepmd import make_deepmd_task_dirs
from ai2_kit.core.util import cmd_with_checkpoint as cmd_cp
from ai2_kit.domain.constant import DP_INPUT_FILE, DP_ORIGINAL_MODEL, DP_FROZEN_MODEL

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dispatcher import BaseApp, PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import bash_iter_ls_slice, safe_ln, get_ln_cmd
from dflow_galaxy.core import types

from dflow import argo_range


INIT_DATASET_DIR = './init-dataset'
ITER_DATASET_DIR = './iter-dataset'

class DeepmdApp(BaseApp):
    dp_cmd: str = 'dp'
    concurrency: int = 4


class DeepmdConfig(BaseModel):
    model_num: int = 4
    init_dataset: List[str] = []
    input_template: dict = {}
    compress_model: bool = False


@dataclass(frozen=True)
class UpdateNewTrainingDatasetArgs:
    label_output_dir: types.InputArtifact
    dataset_dir: types.OutputArtifact


class UpdateNewTrainingDatasetStep:
    def __init__(self, config: DeepmdConfig):
        self.config = config

    def __call__(self, args: UpdateNewTrainingDatasetArgs):
        ...


@dataclass(frozen=True)
class SetupDeepmdTasksArgs:
    init_dataset: types.InputArtifact
    iter_dataset: types.InputArtifact

    work_dir: types.OutputArtifact


class SetupDeepmdTaskFn:
    def __init__(self, config: DeepmdConfig, type_map: List[str]):
        self.config = config
        self.type_map = type_map

    def __call__(self, args: SetupDeepmdTasksArgs):
        # dflow didn't provide a unified file namespace,
        # so we have to link dataset to a fixed path and use relative path to access it
        safe_ln(args.init_dataset, INIT_DATASET_DIR)
        safe_ln(args.iter_dataset, ITER_DATASET_DIR)

        # TODO: handle iter dataset
        train_dataset_dirs = [ f'{INIT_DATASET_DIR}/{ds}' for ds in self.config.init_dataset]

        make_deepmd_task_dirs(input_template=self.config.input_template,
                              model_num=self.config.model_num,
                              train_systems=train_dataset_dirs,
                              type_map=self.type_map,
                              base_dir=args.work_dir,
                              # TODO: support the following parameters
                              isolate_outliers=False,
                              validation_systems=[],
                              outlier_systems=[],
                              outlier_weight=-1.0,
                              dw_input_template=None,
                              )


@dataclass(frozen=True)
class RunDeepmdTrainingArgs:
    slice_idx: types.InputParam[types.SliceIndex]

    init_dataset: types.InputArtifact
    iter_dataset: types.InputArtifact

    work_dir: types.InputArtifact
    persist_dir: types.OutputArtifact


class RunDeepmdTrainingFn:
    def __init__(self, config: DeepmdConfig, context: DeepmdApp):
        self.config = config
        self.context = context

    def __call__(self, args: RunDeepmdTrainingArgs):
        """generate bash script to run deepmd training commands"""
        c = self.context.concurrency

        script = [
            f"pushd {args.work_dir}",
            bash_iter_ls_slice(
                '*/', opt='-d', n=c, i=args.slice_idx, it_var='ITEM',
                script=[
                    '# dp train',
                    'pushd $ITEM',
                    'mv persist/* . || true  # recover checkpoint',
                    get_ln_cmd(args.init_dataset, INIT_DATASET_DIR),
                    get_ln_cmd(args.iter_dataset, ITER_DATASET_DIR),
                    '',
                    self._build_dp_train_script(),
                    '',
                    '# persist result',
                    f'PERSIST_DIR={args.persist_dir}/$ITEM/persist/',
                    'mkdir -p $PERSIST_DIR',
                    'mv *.done $PERSIST_DIR',
                    f'mv {DP_FROZEN_MODEL} $PERSIST_DIR',
                    f'mv {DP_ORIGINAL_MODEL} $PERSIST_DIR || true',
                    'popd',
                ]
            ),
            'popd',
        ]
        return script

    def _build_dp_train_script(self):
        dp_cmd = self.context.dp_cmd
        train_cmd = f'{dp_cmd} train {DP_INPUT_FILE}'
        # TODO: handle restart, initialize from previous model, support pretrain model
        script = [
            cmd_cp(train_cmd, 'dp-train.done'),
            cmd_cp(f'{dp_cmd} freeze -o {DP_ORIGINAL_MODEL}', 'dp-freeze.done'),
        ]
        # compress (optional) and frozen model
        if self.config.compress_model:
            freeze_cmd = f'{dp_cmd} compress -i {DP_ORIGINAL_MODEL} -o {DP_FROZEN_MODEL}'
        else:
            freeze_cmd = f'mv {DP_ORIGINAL_MODEL} {DP_FROZEN_MODEL}'
        script.append(cmd_cp(freeze_cmd, 'dp-compress.done'))

        return '\n'.join(script)


def deepmd_provision(builder: DFlowBuilder, ns: str, /,
                     config: DeepmdConfig,
                     executor: ExecutorConfig,
                     deepmd_app: DeepmdApp,
                     python_app: PythonApp,
                     work_dir_url: str,
                     init_dataset_url: str,
                     iter_dataset_url: str,
                     type_map: List[str],
                     ):

    setup_task_fn = SetupDeepmdTaskFn(config, type_map)
    setup_task_step = builder.make_python_step(setup_task_fn, uid=f'{ns}-setup-task',
                                               setup_script=python_app.setup_script,
                                               executor=create_dispatcher(executor, python_app.resource))(
        SetupDeepmdTasksArgs(
            init_dataset=init_dataset_url,
            iter_dataset=iter_dataset_url,
            work_dir=work_dir_url,
        )
    )
    run_training_fn = RunDeepmdTrainingFn(config=config, context=deepmd_app)
    run_training_step = builder.make_bash_step(run_training_fn, uid=f'{ns}-run-training',
                                               setup_script=deepmd_app.setup_script,
                                               with_param=argo_range(deepmd_app.concurrency),
                                               executor=create_dispatcher(executor, deepmd_app.resource))(
        RunDeepmdTrainingArgs(
            slice_idx="{{item}}",
            init_dataset=init_dataset_url,
            iter_dataset=iter_dataset_url,
            work_dir=work_dir_url,
            persist_dir=work_dir_url,
        )
    )

    builder.add_step(setup_task_step)
    builder.add_step(run_training_step)
