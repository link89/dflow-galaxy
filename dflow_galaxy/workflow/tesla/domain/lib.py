from typing import List, Literal
from ai2_kit.core.artifact import Artifact, ArtifactDict
import glob
from dflow_galaxy.core.util import yes_or_no


LabelApp = Literal['cp2k', 'vasp', 'abacus', 'dpa2']
TrainApp = Literal['deepmd']
ExploreApp = Literal['lammps']


def resolve_artifact(a: Artifact) -> List[ArtifactDict]:
    a_dict = a.to_dict()

    if a.includes is not None:
        urls = glob.glob(f'{a.url}/{a.includes}')
        return [{**a_dict, 'url': url, 'includes': None } for url in urls ]
    return [a_dict]


def resolve_artifacts(a_list: List[Artifact]) -> List[ArtifactDict]:
    result = []
    for a in a_list:
        result.extend(resolve_artifact(a))
    return result


class StepSwitch:
    def __init__(self, enable: bool):
        """
        Control whether to skip a step.

        If enable is False, the step will never be skipped

        Otherwise, the step will be skipped by default,
        unless user answer yes to not skip it.
        And the answer will be remembered so that the following steps will
        """
        self._skip = enable

    def shall_skip(self, step: str):
        if self._skip:
            self._skip = yes_or_no(f'Do you want to skip this step: {step}?', default=True)
        return self._skip
