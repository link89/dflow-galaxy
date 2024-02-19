from typing import List
from dataclasses import dataclass
from dflow_galaxy.core import dflow, types
from dflow_galaxy.core.pydantic import BaseModel


class DeepmdConfig(BaseModel):
    model_num: int = 4
    init_dataset: List[str] = []
    input_template: dict = dict()
    compress_model: bool = False



@dataclass(frozen=True)
class SetupDeepmdTasksArgs:
    input_datasets: types.InputArtifact
    output_dir: types.OutputArtifact


def make_deepmd_step(config: DeepmdConfig,
                     type_map: List[str],
                     source_map: List[str],
                     ):


    def setup_deepmd_tasks(args: SetupDeepmdTasksArgs):
        """
        Generate files with numbers from 0 to input.num and write to output_dir
        """
        ensure_dir(args.output_dir)
        for i in range(args.num):
            out_file = f'{args.output_dir}/file_{i}.txt'
            with open(out_file, 'w') as f:
                f.write(str(i))


    return setup_deepmd_tasks



