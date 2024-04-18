import dflow
from dflow.plugins import bohrium
from dflow.plugins.bohrium import TiefblueClient

from typing import Optional
import getpass
import os


def bohrium_nb_setup_dflow(username: Optional[str], password: Optional[str] = None, project_id: Optional[int] = None):
    if username is None:
        username = input("Enter Bohrium Email: ")
    if password is None:
        password = getpass.getpass("Enter Bohrium password: ")
    if project_id is None:
        project_id = int(os.environ.get("PROJECT_ID"))  # type: ignore

    dflow.config["host"] = "https://workflows.deepmodeling.com"
    dflow.config["k8s_api_server"] = "https://workflows.deepmodeling.com"
    bohrium.config["username"] = username
    bohrium.config["password"] = password
    bohrium.config["project_id"] = project_id
    dflow.s3_config["repo_key"] = "oss-bohrium"
    dflow.s3_config["storage_client"] = TiefblueClient()
