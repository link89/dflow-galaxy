
from dflow_galaxy.core.dispatcher import BaseApp


class Cp2kContext(BaseApp):
    cp2k_cmd: str = 'cp2k.popt'
    concurrency: int = 5
