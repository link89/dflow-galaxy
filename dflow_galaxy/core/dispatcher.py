from .pydantic import BaseModel


from dflow.plugins.dispatcher import DispatcherExecutor
from pydantic import root_validator, ValidationError
from typing import Optional
from urllib.parse import urlparse


class ResourcePlan(BaseModel):
    queue: str
    container: Optional[str]
    remote_dir: str = './dflow'
    node_per_task: int = 1
    cpu_per_node: int = 1

class BohriumConfig(BaseModel):
    email: str

class HpcConfig(BaseModel):
    class SlurmConfig(BaseModel):
        ...
    class LsfConfig(BaseModel):
        ...
    class PBSConfig(BaseModel):
        ...


    url: str
    """
    SSH URL to connect to the HPC, for example: `john@hpc-login01`
    """
    key_file: Optional[str]
    """
    Path to the private key file for SSH connection
    """
    slurm: Optional[SlurmConfig]
    lsf: Optional[LsfConfig]
    pbs: Optional[PBSConfig]

    def get_context_type(self):
        if self.slurm:
            return 'Slurm'
        if self.lsf:
            return 'LSF'
        if self.pbs:
            return 'PBS'
        raise ValueError('At least one of slurm, lsf or pbs should be provided')


class ExecutorConfig(BaseModel):
    hpc: Optional[HpcConfig] = None
    bohrium: Optional[BohriumConfig] = None


def create_dispatcher(config: ExecutorConfig, resource_plan: ResourcePlan) -> dict:
    """
    Create a dispatcher executor based on the configuration
    """
    if config.hpc:
        return create_hpc_dispatcher(config.hpc)
    elif config.bohrium:
        ...
    raise ValueError('At least one of hpc or bohrium should be provided')


def create_hpc_dispatcher(config: HpcConfig) -> dict:
    url = urlparse(config.url)
    assert url.username, 'Username is required in the URL'
    remote_profile = {
        'context_type': config.get_context_type(),
    }
    if config.key_file:
        remote_profile['key_filename'] = config.key_file

    return dict(
        host=url.hostname,
        username=url.username,
        port=url.port or 22,
        machine_dict=dict(
            remote_profile=remote_profile,
        )
    )
