from typing import Optional

from ai2_kit.core.util import load_yaml_files
from ai2_kit.core.cmd import CmdGroup

from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import not_none

from .config import TeslaConfig
from .domain import deepmd, lammps, model_devi, cp2k
from .domain.lib import StepSwitch


class RuntimeContext:
    train_url: Optional[str]
    explore_url: Optional[str]
    screen_url: Optional[str]
    label_url: Optional[str]


def run_tesla(*config_files: str, s3_prefix: str, debug: bool = False, skip: bool = False, iters: int = 1):
    config_raw = load_yaml_files(*config_files)
    config = TeslaConfig(**config_raw)
    config.init()

    type_map = config.workflow.general.type_map
    mass_map = config.workflow.general.mass_map

    builder = DFlowBuilder(name='tesla', s3_prefix=s3_prefix, debug=debug)
    step_switch = StepSwitch(skip)
    runtime_ctx = RuntimeContext()

    for iter_num in range(iters):
        iter_str = f'{iter_num:03d}'

        # Labeling
        cp2k_cfg = config.workflow.label.cp2k
        if cp2k_cfg:
            step_name = f'label-cp2k-iter-{iter_str}'
            runtime_ctx.label_url = f's3://./label-cp2k/iter/{iter_str}'
            cp2k_executor = not_none(config.executors[not_none(config.orchestration.cp2k)])
            if not step_switch.shall_skip(step_name) and \
                (iter_num > 0 or cp2k_cfg.init_systems):  # skip iter 0 if no init systems provided
                assert iter_num == 0 and runtime_ctx.explore_url is None, 'explore_url should be None for iter 0'
                for sys_key in cp2k_cfg.init_systems:
                    sys = not_none(config.datasets[sys_key])
                    builder.s3_upload(sys.url, f'init-systems/{sys_key}', cache=True)
                cp2k.provision_cp2k(builder, step_name,
                                    config=cp2k_cfg,
                                    executor=cp2k_executor,
                                    cp2k_app=not_none(cp2k_executor.apps.cp2k),
                                    python_app=not_none(cp2k_executor.apps.python),

                                    system_url=runtime_ctx.explore_url or 's3://./init-systems',
                                    work_dir_url=runtime_ctx.label_url,

                                    init=(iter_num == 0),
                                    systems=config.datasets,)

        # Training
        deepmd_cfg = config.workflow.train.deepmd
        if deepmd_cfg:
            step_name = f'train-deepmd-iter-{iter_str}'
            runtime_ctx.train_url = f's3://./train-deepmd/iter/{iter_str}'
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
                                        work_dir_url=runtime_ctx.train_url,
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
                    builder.s3_upload(sys.url, f'explore-systems/{sys_key}', cache=True)

                lammps.provision_lammps(builder, step_name,
                                        config=lammps_cfg,
                                        executor=lammps_executor,
                                        lammps_app=not_none(lammps_executor.apps.lammps),
                                        python_app=not_none(lammps_executor.apps.python),

                                        mlp_model_url=runtime_ctx.train_url,
                                        systems_url='s3://./explore-systems',
                                        work_dir_url=runtime_ctx.explore_url,
                                        type_map=type_map,
                                        mass_map=mass_map,
                                        systems=config.datasets)
        else:
            raise ValueError('No explore app specified')

        # Screening
        model_devi_cfg = config.workflow.screen.model_devi
        if model_devi_cfg:
            step_name = f'screen-model-devi-iter-{iter_str}'
            runtime_ctx.screen_url = f's3://./screen-model-devi/iter/{iter_str}'
            model_devi_executor = not_none(config.executors[not_none(config.orchestration.model_devi)])

            if not step_switch.shall_skip(step_name):
                model_devi.provision_model_devi(builder, step_name,
                                                config=model_devi_cfg,
                                                executor=model_devi_executor,
                                                python_app=not_none(model_devi_executor.apps.python),

                                                explore_data_url=runtime_ctx.explore_url,
                                                persist_data_url=runtime_ctx.screen_url,
                                                type_map=type_map)
        else:
            raise ValueError('No screen app specified')


    builder.run()



cmd_entry = CmdGroup({
    'run': run_tesla,
}, doc='TESLA workflow')
