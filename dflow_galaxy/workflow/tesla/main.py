from typing import Mapping, List

from ai2_kit.core.util import load_yaml_files
from ai2_kit.core.cmd import CmdGroup
from ai2_kit.core.artifact import Artifact

from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core.util import not_none

from .config import TeslaConfig
from .domain import deepmd, lammps



def run_tesla(*config_files: str, s3_prefix: str, debug: bool = False):
    # TODO: fix type issue in ai2-kit
    config_raw = load_yaml_files(*config_files)  # type: ignore

    builder = DFlowBuilder(name='tesla', s3_prefix=s3_prefix, debug=debug)

    config = TeslaConfig(**config_raw)

    type_map = config.workflow.general.type_map
    mass_map = config.workflow.general.mass_map
    max_iter = config.workflow.general.max_iters


    for iter_num in range(max_iter):
        iter_str = f'{iter_num:03d}'

        # Training
        deepmd_cfg = config.workflow.train.deepmd
        if deepmd_cfg:
            deepmd_executor = not_none(config.executors[not_none(config.orchestration.deepmd)])
            for ds_key in deepmd_cfg.init_dataset:
                ds = not_none(config.datasets[ds_key])
                builder.s3_upload(ds.url, f'init-dataset/{ds_key}', cache=True)  # set cache to avoid re-upload
            deepmd.deepmd_provision(builder, f'train-deepmd-iter-{iter_str}',
                                    config=deepmd_cfg,
                                    executor=deepmd_executor,
                                    deepmd_app=not_none(deepmd_executor.apps.deepmd),
                                    python_app=not_none(deepmd_executor.apps.python),

                                    init_dataset_url='s3://./init-dataset',
                                    iter_dataset_url='s3://./iter-dataset',
                                    work_dir_url=f's3://./train-deepmd/iter/{iter_str}',
                                    type_map=type_map)
        else:
            raise ValueError('No training app specified')

        # Exploration
        lammps_cfg = config.workflow.explore.lammps
        if lammps_cfg:
            lammps_executor = not_none(config.executors[not_none(config.orchestration.lammps)])
            for sys_key in lammps_cfg.dataset:
                sys = not_none(config.datasets[sys_key])
                builder.s3_upload(sys.url, f'explore-dataset/{sys_key}', cache=True)
            lammps.lammps_provision(builder, f'explore-lammps-iter-{iter_str}',
                                    config=lammps_cfg,
                                    executor=lammps_executor,
                                    lammps_app=not_none(lammps_executor.apps.lammps),
                                    python_app=not_none(lammps_executor.apps.python),

                                    dataset_url='s3://./explore-dataset',
                                    work_dir_url=f's3://./explore-lammps/iter/{iter_str}',
                                    type_map=type_map,
                                    mass_map=mass_map)
        else:
            raise ValueError('No explore app specified')


        # TODO: screen
        # TODO: label

    builder.run()



cmd_entry = CmdGroup({
    'run': run_tesla,
}, doc='TESLA workflow')
