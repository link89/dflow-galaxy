from dflow_galaxy.core.dispatcher import BaseApp


class LammpsContext(BaseApp):
    lammps_cmd: str = 'lmp'
    concurrency: int = 5

