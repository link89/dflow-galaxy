from typing import List, Optional, Mapping, Any, Literal, Tuple
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
import glob
import os
import re

from joblib import Parallel, delayed
from tabulate import tabulate
import pandas as pd
import ase.io

from dflow_galaxy.core.pydantic import BaseModel

from dflow_galaxy.core.dispatcher import PythonApp, create_dispatcher, ExecutorConfig
from dflow_galaxy.core.dflow import DFlowBuilder
from dflow_galaxy.core import types

from ai2_kit.core.util import load_text

class ModelDeviConfig(BaseModel):
    metric: Literal["max_devi_v",  "min_devi_v",  "avg_devi_v",  "max_devi_f",  "min_devi_f",  "avg_devi_f"] = 'max_devi_f'
    decent_range: Tuple[float, float]


@dataclass(frozen=True)
class ModelDeviArgs:
    explore_dir: types.InputArtifact
    work_dir: types.OutputArtifact


_ModelDeviResult = namedtuple('_ModelDeviResult', ['data_dir', 'decent_files', 'ancestor', 'total', 'n_good', 'n_decent', 'n_bad'])

class RunModelDeviTasksFn:

    def __init__(self, config: ModelDeviConfig, workers: int, type_map: List[str]):
        self.config = config
        self.workers = workers
        self.type_map = type_map

    def __call__(self, args: ModelDeviArgs):
        data_dirs = glob.glob(f'{args.explore_dir}/tasks/*')
        results: List[_ModelDeviResult] = Parallel(n_jobs=self.workers)(
            delayed(self._process_lammps_dir)(Path(d) for d in data_dirs)
        ) # type: ignore

        # process results
        headers = ['src', 'total', 'good', 'decent', 'bad', 'good%', 'decent%', 'poor%']
        rows = [ ]
        _pp = lambda a, b: f'{a / b * 100:.2f}%'
        for r in results:
            row = [r.data_dir, r.total, r.n_good, r.n_decent,
                   _pp(r.n_good, r.total), _pp(r.n_decent, r.total), _pp(r.n_bad, r.total)]
            rows.append(row)

        report_text = tabulate(rows, headers=headers, tablefmt='tsv')



    def _process_lammps_dir(self, data_dir: Path):
        col = self.config.metric

        model_devi_file = data_dir / 'model_devi.out'
        traj_dir = data_dir / 'traj'

        with open(model_devi_file, 'r') as f:
            f.seek(1)  # skip the first letter '#'
            df = pd.read_csv(f, delim_whitespace=True)
        lo, hi = self.config.decent_range

        good_df = df[df[col] < lo]
        decent_df = df[(df[col] >= lo) & (df[col] < hi)]
        bad_df = df[df[col] > hi]

        traj_files = glob.glob(f'{traj_dir}/*.lammpstrj')
        assert traj_files, f'no traj files is found in {traj_dir}'

        traj_files = sorted(traj_files, key=_get_lammpstraj_frame_no)  # align

        decent_files = [traj_files[i] for i in decent_df.index]

        return _ModelDeviResult(
            data_dir=data_dir,
            decent_files=decent_files,
            ancestor=load_text(data_dir / 'ANCESTOR'),
            total=len(df),
            n_good=len(good_df),
            n_decent=len(decent_df),
            n_bad=len(bad_df),
        )



def _get_lammpstraj_frame_no(filename):
    m = re.match(r'^(\d+)', filename)
    assert m, f'unexpected lammpstraj file name: {filename}'
    return int(m.group(1))



def provision_model_devi(builder: DFlowBuilder, ns: str, /,
                         config: ModelDeviConfig,
                         executor: ExecutorConfig,
                         python_app: PythonApp,
                         ):
    run_task_fn = RunModelDeviTasksFn(config, workers=python_app.max_worker)


