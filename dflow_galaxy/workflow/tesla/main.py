from ai2_kit.core.util import load_yaml_files
from ai2_kit.core.cmd import CmdGroup

from dflow_galaxy.core.dflow import DFlowBuilder

from .config import TeslaConfig


def run_tesla(*config_files: str, name: str, s3_prefix: str, debug: bool = False):
    config_raw = load_yaml_files(*config_files)  # TODO: fix type issue in ai2-kit

    dflow_builder = DFlowBuilder(name=name,
                                 s3_prefix=s3_prefix,
                                 debug=debug)

    config = TeslaConfig(**config_raw)
    workflow_cfg = config.workflow

    # training
    if workflow_cfg.train.deepmd:
        ...
    else:
        raise ValueError('No training app specified')

















