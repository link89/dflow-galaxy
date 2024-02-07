from typing import TypeVar, Annotated
from enum import IntEnum, auto

T = TypeVar('T')
class Symbol(IntEnum):
    INPUT_PARAMETER = auto()
    INPUT_ARTIFACT = auto()
    OUTPUT_PARAMETER = auto()
    OUTPUT_ARTIFACT = auto()


InputParam = Annotated[T, Symbol.INPUT_PARAMETER]
InputArtifact = Annotated[str, Symbol.INPUT_ARTIFACT]
OutputParam = Annotated[T, Symbol.OUTPUT_PARAMETER]
OutputArtifact = Annotated[str, Symbol.OUTPUT_ARTIFACT]
