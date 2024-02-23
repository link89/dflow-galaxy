from typing import List, Optional, Mapping, Any, Literal, Tuple
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path
from itertools import groupby
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

from ai2_kit.core.util import load_text, dump_text

class ModelDeviConfig(BaseModel):
    metric: Literal["max_devi_v",  "min_devi_v",  "avg_devi_v",  "max_devi_f",  "min_devi_f",  "avg_devi_f"] = 'max_devi_f'
    decent_range: Tuple[float, float]


@dataclass(frozen=True)
class RunModelDeviTasksArgs:
    explore_dir: types.InputArtifact
    persist_dir: types.OutputArtifact

_ModelDeviResult = namedtuple('_ModelDeviResult', ['data_dir', 'decent_xyz', 'ancestor', 'total', 'n_good', 'n_decent', 'n_bad'])

class RunModelDeviTasksFn:

    def __init__(self, config: ModelDeviConfig, workers: int, type_map: List[str]):
        self.config = config
        self.workers = workers
        self.type_map = type_map

    def __call__(self, args: RunModelDeviTasksArgs):
        persis_dir = Path(args.persist_dir)
        data_dirs = sorted(glob.glob(f'{args.explore_dir}/tasks/*/persist'))
        results: List[_ModelDeviResult] = Parallel(n_jobs=self.workers)(
            delayed(self._process_lammps_dir)(Path(d)) for d in data_dirs
        ) # type: ignore

        # generate report
        headers = ['src', 'total', 'good', 'decent', 'bad', 'good%', 'decent%', 'poor%']
        rows = [ ]
        _pp = lambda a, b: f'{a / b * 100:.2f}%'
        for r in results:
            row = [os.path.relpath(r.data_dir, args.explore_dir), r.total, r.n_good, r.n_decent,
                   _pp(r.n_good, r.total), _pp(r.n_decent, r.total), _pp(r.n_bad, r.total)]
            rows.append(row)

        report_text = tabulate(rows, headers=headers, tablefmt='tsv')
        dump_text(report_text, str(persis_dir / 'report.tsv'))

        # dump decent xyz
        results = sorted(results, key=lambda r: r.ancestor)
        for ancestor, group in groupby(results, key=lambda r: r.ancestor):
            assert ancestor, f'ancestor should not be empty'
            group = list(group)
            assert group, f'group should not be empty'
            decent_xyz_files = [r.decent_xyz for r in group if r.decent_xyz is not None]
            if not decent_xyz_files:
                print(f'no decent files for ancestor {ancestor}')
                continue

            result_dir: Path = persis_dir / ancestor
            result_dir.mkdir(exist_ok=True)

            # merge the xyz files
            os.system(f'cat {" ".join(decent_xyz_files)} > {result_dir / "decent.xyz"}')
            dump_text(ancestor, str(result_dir / 'ANCESTOR'))

    def _process_lammps_dir(self, data_dir: Path):
        col = self.config.metric

        model_devi_file = data_dir / 'model_devi.out'
        traj_dir = data_dir / 'traj'

        with open(model_devi_file, 'r') as f:
            f.seek(1)  # skip the leading '#'
            df = pd.read_csv(f, delim_whitespace=True)
        lo, hi = self.config.decent_range

        good_df = df[df[col] < lo]
        decent_df = df[(df[col] >= lo) & (df[col] < hi)]
        bad_df = df[df[col] > hi]

        traj_files = glob.glob(f'{traj_dir}/*.lammpstrj')
        assert traj_files, f'no traj files is found in {traj_dir}'

        # pick decent files
        traj_files = sorted(traj_files, key=get_lammpstrj_frame_no)  # align
        decent_files = [traj_files[i] for i in decent_df.index]

        # merge decent files
        decent_xyz = None
        if len(decent_df) > 0:
            decent_trj = data_dir / 'decent.lammpstrj'
            decent_xyz = data_dir / 'decent.xyz'
            os.system(f'cat {" ".join(decent_files)} > {decent_trj}')
            self._dump_lammpstrj_to_xyz(decent_trj, decent_xyz)

        return _ModelDeviResult(
            data_dir=data_dir,
            decent_xyz=decent_xyz,
            ancestor=load_text(data_dir / 'ANCESTOR'),
            total=len(df),
            n_good=len(good_df),
            n_decent=len(decent_df),
            n_bad=len(bad_df),
        )

    def _dump_lammpstrj_to_xyz(self, lmptrj_file: Path, xyz_file: Path):
        atoms_list = ase.io.read(lmptrj_file, ':', format='lammps-dump-text', specorder=self.type_map)
        ase.io.write(xyz_file, atoms_list, format='extxyz')


def get_lammpstrj_frame_no(filename):
    filename = os.path.basename(filename)
    m = re.match(r'^(\d+)', filename)
    assert m, f'unexpected lammpstrj file name: {filename}'
    return int(m.group(1))


def provision_model_devi(builder: DFlowBuilder, ns: str, /,
                         config: ModelDeviConfig,
                         executor: ExecutorConfig,
                         python_app: PythonApp,
                         type_map: List[str],

                         explore_data_url: str,
                         persist_data_url: str,
                         ):
    run_tasks_fn = RunModelDeviTasksFn(config, workers=python_app.max_worker, type_map=type_map)
    run_tasks_step = builder.make_python_step(run_tasks_fn, uid=f'{ns}-run-task',
                                              setup_script=python_app.setup_script,
                                              executor=create_dispatcher(executor, python_app.resource))(
        RunModelDeviTasksArgs(
            explore_dir=explore_data_url,
            persist_dir=persist_data_url,
        )
    )
    builder.add_step(run_tasks_step)
