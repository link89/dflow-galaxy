from dflow_galaxy.core.dispatcher import BaseAppContext


class LammpsContext(BaseAppContext):
    lammps_cmd: str = 'lmp'
    concurrency: int = 5

