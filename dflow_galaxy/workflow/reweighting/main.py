from typing import Optional
from copy import deepcopy

from ai2_kit.core.util import load_yaml_files, merge_dict
from ai2_kit.core.cmd import CmdGroup

from dflow_galaxy.core.pydantic import BaseModel
from dflow_galaxy.core.dflow_builder import DFlowBuilder
from dflow_galaxy.core.util import not_none
from dflow_galaxy.core.log import get_logger


logger = get_logger(__name__)


class Config(BaseModel):
    baseline_system_dir: str
    """
    The directory contains the baseline system files in dpdata.System or dpdata.LabeledSystem format.
    """

    baseline_colvar_file: str
    """
    Path to the baseline plumed COLVAR file.
    """

    baseline_model_file: Optional[str] = None
    """
    Path to the baseline DeepMD model file.

    If not provided, the baseline system data should be in dpdata.LabeledSystem format.
    """

    test_model_file: str
    """
    Path to the DeepMD model file for testing.
    """


def build_reweighing_workflow(config: Config,
                              s3_prefix: str,
                              debug: bool = False,
                              name: str = 'reweighting'):

    builder = DFlowBuilder(name=name, s3_prefix=s3_prefix, debug=debug,
                           default_archive=None)
