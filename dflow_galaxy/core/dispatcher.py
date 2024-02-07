from .pydantic import BaseModel

from dflow.plugins.dispatcher import DispatcherExecutor
from pydantic import root_validator, ValidationError
from typing import Optional
from urllib.parse import urlparse
import os


class ResourcePlan(BaseModel):
    queue: Optional[str] = None
    container: Optional[str] = None
    work_dir: str = '.'
    nodes: int = 1
    cpus_per_node: int = 1


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
    key_file: Optional[str] = None
    """
    Path to the private key file for SSH connection
    """
    slurm: Optional[SlurmConfig] = None
    lsf: Optional[LsfConfig] = None
    pbs: Optional[PBSConfig] = None
    base_dir: str = '.'

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


def create_dispatcher(config: ExecutorConfig, resource_plan: ResourcePlan) -> DispatcherExecutor:
    """
    Create a dispatcher executor based on the configuration
    """
    if config.hpc:
        return create_hpc_dispatcher(config.hpc, resource_plan)
    elif config.bohrium:
        raise NotImplementedError('Bohrium dispatcher is not implemented yet')
    raise ValueError('At least one of hpc or bohrium should be provided')


def create_hpc_dispatcher(config: HpcConfig, resource_plan: ResourcePlan) -> DispatcherExecutor:
    url = urlparse(config.url)
    assert url.scheme == 'ssh', 'Only SSH is supported for HPC dispatcher'
    assert url.username, 'Username is required in the URL'
    assert os.path.isabs(config.base_dir), 'Base directory must be an absolute path'
    remote_root = os.path.normpath(
        os.path.join(config.base_dir, resource_plan.work_dir))

    remote_profile = { }
    if config.key_file:
        remote_profile['key_filename'] = config.key_file
    resource_dict = {
        'number_node': resource_plan.nodes,
        'cpu_per_node': resource_plan.cpus_per_node,
    }
    machine_dict = {
        "batch_type": config.get_context_type(),
        "context_type": "SSHContext",
        'remote_profile': remote_profile,
    }

    return DispatcherExecutor(
        host=url.hostname or 'localhost',
        username=url.username,
        port=url.port or 22,
        machine_dict=machine_dict,
        resources_dict=resource_dict,
        queue_name=resource_plan.queue,
        remote_root=remote_root,
    )
