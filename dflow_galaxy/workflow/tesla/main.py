from typing import Optional

from ai2_kit.core.util import load_yaml_files
from ai2_kit.core.cmd import CmdGroup

from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import not_none

from .config import TeslaConfig
from .domain import deepmd, lammps
from .domain.lib import StepSwitch


class RuntimeContext:
    mlp_model_url: Optional[str]
    explore_url: Optional[str]


def run_tesla(*config_files: str, s3_prefix: str, debug: bool = False, skip: bool = False):
    # TODO: fix type issue in ai2-kit
    config_raw = load_yaml_files(*config_files)  # type: ignore
    config = TeslaConfig(**config_raw)
    config.init()

    type_map = config.workflow.general.type_map
    mass_map = config.workflow.general.mass_map
    max_iter = config.workflow.general.max_iters

    builder = DFlowBuilder(name='tesla', s3_prefix=s3_prefix, debug=debug)
    step_switch = StepSwitch(skip)
    runtime_ctx = RuntimeContext()

    for iter_num in range(max_iter):
        iter_str = f'{iter_num:03d}'

        # Training
        deepmd_cfg = config.workflow.train.deepmd
        if deepmd_cfg:
            step_name = f'train-deepmd-iter-{iter_str}'
            runtime_ctx.mlp_model_url = f's3://./train-deepmd/iter/{iter_str}'
            deepmd_executor = not_none(config.executors[not_none(config.orchestration.deepmd)])

            if not step_switch.shall_skip(step_name):
                for ds_key in deepmd_cfg.init_dataset:
                    ds = not_none(config.datasets[ds_key])
                    builder.s3_upload(ds.url, f'init-dataset/{ds_key}', cache=True)  # set cache to avoid re-upload
                deepmd.provision_deepmd(builder, step_name,
                                        config=deepmd_cfg,
                                        executor=deepmd_executor,
                                        deepmd_app=not_none(deepmd_executor.apps.deepmd),
                                        python_app=not_none(deepmd_executor.apps.python),

                                        init_dataset_url='s3://./init-dataset',
                                        iter_dataset_url='s3://./iter-dataset',
                                        work_dir_url=runtime_ctx.mlp_model_url,
                                        type_map=type_map)

        else:
            raise ValueError('No training app specified')

        # Exploration
        lammps_cfg = config.workflow.explore.lammps
        if lammps_cfg:
            step_name = f'explore-lammps-iter-{iter_str}'
            runtime_ctx.explore_url = f's3://./explore-lammps/iter/{iter_str}'
            lammps_executor = not_none(config.executors[not_none(config.orchestration.lammps)])

            if not step_switch.shall_skip(step_name):
                for sys_key in lammps_cfg.systems:
                    sys = not_none(config.datasets[sys_key])
                    builder.s3_upload(sys.url, f'explore-dataset/{sys_key}', cache=True)

                lammps.provision_lammps(builder, step_name,
                                        config=lammps_cfg,
                                        executor=lammps_executor,
                                        lammps_app=not_none(lammps_executor.apps.lammps),
                                        python_app=not_none(lammps_executor.apps.python),

                                        mlp_model_url=runtime_ctx.mlp_model_url,
                                        systems_url='s3://./explore-dataset',
                                        work_dir_url=runtime_ctx.explore_url,
                                        type_map=type_map,
                                        mass_map=mass_map,
                                        systems=config.datasets)
        else:
            raise ValueError('No explore app specified')


        # TODO: screen
        # TODO: label

    builder.run()



cmd_entry = CmdGroup({
    'run': run_tesla,
}, doc='TESLA workflow')
