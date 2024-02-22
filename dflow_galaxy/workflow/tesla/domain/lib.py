from typing import List
from ai2_kit.core.artifact import Artifact, ArtifactDict
import glob


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
