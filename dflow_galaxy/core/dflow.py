from dflow.op_template import ScriptOPTemplate
import dflow

from typing import Final, Callable, TypeVar, Optional, Union, Annotated, Generic, Dict, Any, Iterable
from dataclasses import fields, is_dataclass, asdict
from urllib.parse import urlparse, parse_qs
from collections import namedtuple
from enum import IntEnum, auto
from pathlib import Path
from uuid import uuid4
import cloudpickle as cp
import tempfile
import tarfile
import hashlib
import inspect
import base64
import shutil
import bz2
import os

from .log import get_logger
logger = get_logger(__name__)


T = TypeVar('T')
T_IN = TypeVar('T_IN')
T_OUT = TypeVar('T_OUT')


class Symbol(IntEnum):
    INPUT_PARAMETER = auto()
    INPUT_ARTIFACT = auto()
    OUTPUT_PARAMETER = auto()
    OUTPUT_ARTIFACT = auto()


InputParam = Annotated[T, Symbol.INPUT_PARAMETER]
InputArtifact = Annotated[str, Symbol.INPUT_ARTIFACT]
OutputParam = Annotated[T, Symbol.OUTPUT_PARAMETER]
OutputArtifact = Annotated[str, Symbol.OUTPUT_ARTIFACT]

DFLOW_ARTIFACT = Union[str, dflow.S3Artifact, dflow.OutputArtifact, dflow.InputArtifact]


class Step(Generic[T_IN, T_OUT]):
    def __init__(self, df_step: dflow.Step):
        self.df_step = df_step

    @property
    def inputs(self) -> T_IN:
        return ObjProxy(self.df_step.inputs.parameters,
                        self.df_step.inputs.artifacts,
                        self.df_step.outputs.artifacts)  # type: ignore

    @property
    def outputs(self) -> T_OUT:
        return ObjProxy(self.df_step.outputs.parameters)  # type: ignore


class ObjProxy:
    def __init__(self, *obj):
        self.objs = obj

    def __getattr__(self, name):
        for obj in self.objs:
            if hasattr(obj, name):
                return getattr(obj, name)
            elif name in obj:
                return obj[name]
        raise AttributeError(f'{name} not found in {self.objs}')


def pickle_converts(obj, pickle_module='cp', bz2_module='bz2', base64_module='base64'):
    """
    convert an object to its pickle string form
    """
    obj_pkl = cp.dumps(obj, protocol=cp.DEFAULT_PROTOCOL)
    compress_level = 5 if len(obj_pkl) > 4096 else 1
    compressed = bz2.compress(obj_pkl, compress_level)
    obj_b64 = base64.b64encode(compressed).decode('ascii')
    return f'{pickle_module}.loads({bz2_module}.decompress({base64_module}.b64decode({repr(obj_b64)})))'


def iter_python_step_args(obj):
    """
    Iterate over the input fields of a python step.
    A python step input should be:
    1. A frozen dataclass.
    2. All fields are annotated with InputParam, InputArtifact or OutputArtifact.
    """
    assert is_dataclass(obj), f'{obj} is not a dataclass'
    assert obj.__dataclass_params__.frozen, f'{obj} is not frozen'
    for f in fields(obj):
        msg = f'{f.name} is not annotated with InputParam, InputArtifact or OutputArtifact'
        assert hasattr(f.type, '__metadata__'), msg
        assert f.type.__metadata__[0] in (
            Symbol.INPUT_PARAMETER, Symbol.INPUT_ARTIFACT,
            Symbol.OUTPUT_ARTIFACT), msg
        yield f, getattr(obj, f.name, None)


def iter_python_step_return(obj):
    """
    Iterate over the output fields of a python step.
    A python step output should be:
    1. A dataclass.
    2. All fields are annotated with OutputParam.
    """
    if obj is inspect.Signature.empty or obj is None:
        return

    assert is_dataclass(obj), f'{obj} is not a dataclass'
    for f in fields(obj):
        msg = f'{f.name} is not annotated with OutputParam'
        assert hasattr(f.type, '__metadata__'), msg
        assert f.type.__metadata__ [0] == Symbol.OUTPUT_PARAMETER, msg
        yield f, getattr(obj, f.name, None)


_PythonTemplate = namedtuple('_PythonStep', ['source', 'fn_str', 'script_path', 'pkg_dir',
                                             'dflow_input_parameters',
                                             'dflow_input_artifacts',
                                             'dflow_output_parameters',
                                             'dflow_output_artifacts',
                                             ])


def python_build_template(py_fn: Callable,
                          base_dir: str) -> _PythonTemplate:
    """
    build python template from a python function
    """
    sig = inspect.signature(py_fn)
    assert len(sig.parameters) == 1, f'{py_fn} should have only one parameter'
    args_type = sig.parameters[next(iter(sig.parameters))].annotation
    return_type  = sig.return_annotation

    fn_dir = os.path.join(base_dir, 'python/fn')
    pkg_dir = os.path.join(base_dir, 'python/pkg')
    args_file = os.path.join(fn_dir, 'args.json')
    script_path = os.path.join(fn_dir, 'script.py')
    output_parameters_dir = os.path.join(base_dir, 'output-parameters')
    output_artifacts_dir = os.path.join(base_dir, 'output-artifacts')

    dflow_input_parameters: Dict[str, dflow.InputParameter] = {}
    dflow_input_artifacts: Dict[str, dflow.InputArtifact] = {}
    dflow_output_artifacts: Dict[str, dflow.OutputArtifact] = {}
    dflow_output_parameters: Dict[str, dflow.OutputParameter] = {}

    source = [
        'import os, json, tarfile',
        f'base_dir = {repr(base_dir)}',
        f'fn_dir = {repr(fn_dir)}',
        f'pkg_dir = {repr(pkg_dir)}',
        f'args_file = {repr(args_file)}',
        f'script_path = {repr(script_path)}',
        f'output_parameters_dir = {repr(output_parameters_dir)}',
        f'output_artifacts_dir = {repr(output_artifacts_dir)}',
        'os.makedirs(fn_dir, exist_ok=True)',
        'os.makedirs(pkg_dir, exist_ok=True)',
        'os.makedirs(output_parameters_dir, exist_ok=True)',
        'os.makedirs(output_artifacts_dir, exist_ok=True)',
        'args = dict()',
    ]

    for f, v in iter_python_step_args(args_type):
        if f.type.__metadata__[0] == Symbol.INPUT_PARAMETER:
            # FIXME: may have error in some corner cases
            if issubclass(f.type.__origin__, str):
                val = f'"""{{{{inputs.parameters.{f.name}}}}}"""'
            else:
                val = f'json.loads("""{{{{inputs.parameters.{f.name}}}}}""")'
            dflow_input_parameters[f.name] = dflow.InputParameter(name=f.name)
            source.append(f'args[{repr(f.name)}] = {val}')
        elif f.type.__metadata__[0] == Symbol.INPUT_ARTIFACT:
            path = os.path.join(base_dir, 'input-artifacts', f.name)
            dflow_input_artifacts[f.name] = dflow.InputArtifact(path=path)
            source.append(f'args[{repr(f.name)}] = {repr(path)}')
        elif f.type.__metadata__[0] == Symbol.OUTPUT_ARTIFACT:
            path = os.path.join(output_artifacts_dir, f.name)
            dflow_output_artifacts[f.name] = dflow.OutputArtifact(path=Path(path))
            source.append(f'args[{repr(f.name)}] = {repr(path)}')

    source.extend([
        '',
        'with open(args_file, "w") as fp:',
        '    json.dump(args, fp, indent=2)',
        '',
        '# unpack tarball in pkg_dir',
        'for file in os.listdir(pkg_dir):',
        '    if file.endswith(".tar.bz2"):',
        '        with tarfile.open(os.path.join(pkg_dir, file), "r:bz2") as tar_fp:',
        '            tar_fp.extractall(pkg_dir)',
        '',
        '# insert pkg_dir to PYTHONPATH',
        'os.environ["PYTHONPATH"] = pkg_dir + ":" + os.environ.get("PYTHONPATH", "")',
        'os.system(f"python {script_path} {args_file}")',
    ])

    fn_str = [
        'import cloudpickle as cp',
        'import base64, json, bz2, os, sys',
        '',
        '# deserialize function',
        f'__fn = {pickle_converts(py_fn)}',
        '',
        '# deserialize args type',
        f'__ArgsType = {pickle_converts(args_type)}',
        '',
        '# run the function',
        'with open(sys.argv[1], "r") as fp:',
        '    __args = __ArgsType(**json.load(fp))',
        '__ret = __fn(__args)',
        '',
        '# handle the return value',
    ]

    for f, v in iter_python_step_return(return_type):
        path = os.path.join(output_parameters_dir, f.name)
        if issubclass(f.type.__origin__, str):
            fn_str.extend([
                f'with open({repr(path)}, "w") as fp:',
                f'    fp.write(str(__ret.{f.name}))'
            ])
        else:
            fn_str.extend([
                f'with open({repr(path)}, "w") as fp:',
                f'    json.dump(__ret.{f.name}, fp)'
            ])
        dflow_output_parameters[f.name] = dflow.OutputParameter(value_from_path=path)

    for line in source:
        assert '/tmp' not in line.replace(base_dir, ''), 'dflow: script should not contain unexpected /tmp literal'

    return _PythonTemplate(source='\n'.join(source),
                           fn_str='\n'.join(fn_str),
                           script_path=script_path,
                           pkg_dir=pkg_dir,
                           dflow_input_parameters=dflow_input_parameters,
                           dflow_input_artifacts=dflow_input_artifacts,
                           dflow_output_parameters=dflow_output_parameters,
                           dflow_output_artifacts=dflow_output_artifacts)


class DFlowBuilder:
    """
    A type friendly wrapper to build a DFlow workflow.
    """

    def __init__(self, name:str, s3_prefix: str, base_dir: str = '/tmp/dflow-builder', debug=False, s3_debug_fn = shutil.copy):
        """
        :param name: The name of the workflow.
        :param s3_prefix: The base prefix of the S3 bucket to store data generated by the workflow.
        :param base_dir: The base directory to mapping resources in remote container.
        :param debug: If True, the workflow will be run in debug mode.
        :param s3_debug_fn: The function to upload file to S3 under debug mode.
        """
        if debug:
            dflow.config['mode'] = 'debug'
            s3_prefix = s3_prefix.lstrip('/')

        assert base_dir.startswith('/tmp'), 'dflow: base_dir must be a subdirectory of /tmp'

        self.name: Final[str] = name
        self.s3_prefix: Final[str] = s3_prefix
        self.base_dir: Final[str] = base_dir
        self.workflow: Final[dflow.Workflow] = dflow.Workflow(name=name)
        self._python_fns: Dict[Callable, str] = {}
        self._python_pkgs: Dict[str, str] = {}
        self._s3_debug_fn = s3_debug_fn
        self._debug = debug

    def add_python_pkg(self, pkg: str):
        """
        Add a python package to the workflow.
        """
        # Find the path of target package,
        # then create a temporary tarball and upload it to s3

        if pkg not in self._python_pkgs:
            pkg_path = os.path.dirname(__import__(pkg).__file__)
            with tempfile.NamedTemporaryFile(suffix='.tar.bz2') as fp:
                with tarfile.open(fp.name, 'w:bz2') as tar_fp:
                    tar_fp.add(pkg_path, arcname=os.path.basename(pkg_path), filter=_filter_pyc_files)
                fp.flush()
                key = self.s3_upload(Path(fp.name), 'build-in/python/pkg', f'{pkg}.tar.bz2')
                logger.info(f'upload {pkg} to {key}')
                self._python_pkgs[pkg] = key
        return self._python_pkgs[pkg]

    def s3_upload(self, path: os.PathLike, *keys: str) -> str:
        """
        upload local file to S3.

        :param path: The local file path.
        :param keys: The keys of the S3 object.
        """
        key = self._s3_get_key(*keys)
        return dflow.upload_s3(path, key, debug_func=self._s3_debug_fn)

    def s3_dump(self, data: Union[bytes, str], *keys: str) -> str:
        """
        Dump data to s3.

        :param data: The bytes to upload.
        :param keys: The keys of the S3 object.
        """
        mode = 'wb' if isinstance(data, bytes) else 'w'
        with tempfile.NamedTemporaryFile(mode) as fp:
            fp.write(data)
            fp.flush()
            return self.s3_upload(Path(fp.name), *keys)

    def run(self):
        self.workflow.submit()
        self.workflow.wait()

    def make_python_step(self,
                         fn: Callable[[T_IN], T_OUT],
                         with_param: Any = None,
                         uid: Optional[str] = None,
                         pkgs: Optional[Iterable[str]] = None,
                         ) -> Callable[[T_IN], Step[T_IN, T_OUT]]:
        """
        Make a python step.

        :param fn: The python function to run in the step.
        :param with_param: The parameter to pass to the step
        :param uid: The unique id of the step.
        :return: A function to run the step.

        Due to the design flaw of the Argo Workflow that the s3 key cannot be set as step arguments,
        for each step a dedicated template have to be created.
        Ref: https://github.com/argoproj/argo-workflows/discussions/12606#discussioncomment-8358302
        """
        if uid is None:
            uid = str(uuid4())
        if pkgs is None:
            pkgs = ['dflow_galaxy']

        template = self._create_python_template(fn, uid=uid, pkgs=pkgs)
        def wrapped_fn(in_params: T_IN):
            parameters = {}
            artifacts = {}

            for f, v in iter_python_step_args(in_params):
                if f.type.__metadata__[0] == Symbol.INPUT_PARAMETER:
                    parameters[f.name] = v
                elif f.type.__metadata__[0] == Symbol.INPUT_ARTIFACT:
                    artifacts[f.name] = self._s3_parse_url(v)  # type: ignore
                elif f.type.__metadata__[0] == Symbol.OUTPUT_ARTIFACT:
                    template.outputs.artifacts[f.name].save = [self._s3_parse_url(v)]  # type: ignore

            step = dflow.Step(
                name='python-step-' + uid,
                template=template,
                with_param=with_param,
                parameters=parameters,
                artifacts=artifacts,
            )
            return Step(step)
        return wrapped_fn

    def _create_python_template(self, fn: Callable,
                                uid: Optional[str] = None,
                                python_cmd: str = 'python3',
                                pkgs: Optional[Iterable[str]] = None,
                                ):
        if uid is None:
            uid = str(uuid4())
        if pkgs is None:
            pkgs = []
        _template = python_build_template(fn, base_dir=self.base_dir)
        fn_hash = hashlib.sha256(_template.fn_str.encode()).hexdigest()
        dflow_template = ScriptOPTemplate(
            name='python-template-' + uid,
            command=python_cmd,
            script=_template.source,
        )
        dflow_template.inputs.parameters = _template.dflow_input_parameters
        dflow_template.inputs.artifacts = _template.dflow_input_artifacts
        dflow_template.outputs.parameters = _template.dflow_output_parameters
        dflow_template.outputs.artifacts = _template.dflow_output_artifacts
        # upload python script to s3
        key = self._add_python_fn(fn, _template.fn_str, fn_hash)
        dflow_template.inputs.artifacts['__fn__'] = dflow.InputArtifact(
            source=dflow.S3Artifact(key=key),
            path=_template.script_path,
        )
        # download python packages
        for pkg in pkgs:
            key = self.add_python_pkg(pkg)
            dflow_template.inputs.artifacts[pkg] = dflow.InputArtifact(
                source=dflow.S3Artifact(key=key),
                path=os.path.join(_template.pkg_dir, f'{pkg}.tar.bz2'),
            )
        return dflow_template

    def _add_python_fn(self, fn, fn_str: str, fn_hash: str):
        if fn not in self._python_fns:
            fn_prefix = self.s3_dump(fn_str, 'build-in/python/fn', fn_hash)
            logger.info(f'upload {fn} to {fn_prefix}')
            self._python_fns[fn] = fn_prefix
        return self._python_fns[fn]

    def _s3_get_key(self, *keys: str):
        return os.path.join(self.s3_prefix, *keys)

    def _s3_parse_url(self, url: DFLOW_ARTIFACT) -> DFLOW_ARTIFACT:
        if not isinstance(url, str):
            return url
        parsed = urlparse(url)
        if parsed.scheme == 's3':
            key = os.path.join(self.s3_prefix, parsed.path.lstrip('/'))
            if self._debug:
                key = os.path.abspath(key)
            return dflow.S3Artifact(key=key)
        else:
            raise ValueError(f'unsupported url {url}')

def _filter_pyc_files(tarinfo):
    if tarinfo.name.endswith('.pyc') or tarinfo.name.endswith('__pycache__'):
        return None
    return tarinfo