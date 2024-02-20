
from dflow_galaxy.core.dispatcher import BaseAppContext


class Cp2kContext(BaseAppContext):
    cp2k_cmd: str = 'cp2k.popt'
    concurrency: int = 5
