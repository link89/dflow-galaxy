from ai2_kit.core.util import load_yaml_files
from ai2_kit.core.cmd import CmdGroup

from dflow_galaxy.core.dflow import DFlowBuilder

from .config import TeslaConfig
from .domain import deepmd


def run_tesla(*config_files: str, name: str, s3_prefix: str, debug: bool = False):
    # TODO: fix type issue in ai2-kit
    config_raw = load_yaml_files(*config_files)  # type: ignore

    builder = DFlowBuilder(name=name, s3_prefix=s3_prefix, debug=debug)

    config = TeslaConfig(**config_raw)

    type_map = config.workflow.general.type_map
    mass_map = config.workflow.general.mass_map
    max_iter = config.workflow.general.max_iter


    for iter_num in range(max_iter):
        iter_str = f'{iter_num:02d}'

        # training
        deepmd_cfg = config.workflow.train.deepmd
        if deepmd_cfg:
            deepmd_ctx = config.apps.deepmd
            assert deepmd_ctx, 'missing deepmd in apps'

            deepmd_runtime = deepmd.DeepmdRuntime(
                base_url=config.datasets['base'],
                init_dataset_url='TODO',
                type_map=type_map,
            )

            deepmd.deepmd_provision(builder, f'deepmd-train-{iter_str}',
                                    config=deepmd_cfg,
                                    context=deepmd_ctx,
                                    runtime=deepmd_runtime)
        else:
            raise ValueError('No training app specified')

        # TODO: explore
        # TODO: screen
        # TODO: label
