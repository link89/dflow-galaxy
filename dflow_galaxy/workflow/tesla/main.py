from ai2_kit.core.util import load_yaml_files
from ai2_kit.core.cmd import CmdGroup

from dflow_galaxy.core.dflow import DFlowBuilder

from .config import TeslaConfig


def run_tesla(*config_files: str, name: str, s3_prefix: str, debug: bool = False):
    config_raw = load_yaml_files(*config_files)

    dflow_builder = DFlowBuilder(name=name,
                                 s3_prefix=s3_prefix,
                                 debug=debug)

    config = TeslaConfig(**config_raw)


    # training
    if config.workflow.train















