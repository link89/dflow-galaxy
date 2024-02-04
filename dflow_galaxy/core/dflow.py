from dflow.op_template import ScriptOPTemplate
import dflow

from typing import Final, Callable, TypeVar, Optional, Union, Annotated, Dict, Any
from dataclasses import fields, is_dataclass, asdict
from collections import namedtuple
from enum import IntEnum, auto
from pathlib import Path
from uuid import uuid4
import cloudpickle as cp
import tempfile
import hashlib
import inspect
import base64
import bz2
import os


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
        yield f


def iter_python_step_return(obj):
    """
    Iterate over the output fields of a python step.
    A python step output should be:
    1. A dataclass.
    2. All fields are annotated with OutputParam.
    """
    assert is_dataclass(obj), f'{obj} is not a dataclass'
    for f in fields(obj):
        msg = f'{f.name} is not annotated with OutputParam'
        assert hasattr(f.type, '__metadata__'), msg
        assert f.type.__metadata__ [0] == Symbol.OUTPUT_PARAMETER, msg
        yield f


_PythonTemplate = namedtuple('_PythonStep', ['source', 'fn_str',
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

    args_file = os.path.join(base_dir, 'tmp/args.json')
    script_path = os.path.join(base_dir, 'tmp/script.py')
    output_parameters_path = os.path.join(base_dir, 'output-parameters')

    dflow_input_parameters: Dict[str, dflow.InputParameter] = {}
    dflow_input_artifacts: Dict[str, dflow.InputArtifact] = {}
    dflow_output_artifacts: Dict[str, dflow.OutputArtifact] = {}
    dflow_output_parameters: Dict[str, dflow.OutputParameter] = {}

    dflow_input_artifacts['__script__'] = dflow.InputArtifact(path=script_path)

    source = [
        'import os, json',
        '',
        'args = dict()',
    ]

    for f in iter_python_step_args(args_type):
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
            path = os.path.join(base_dir, 'output-artifacts', f.name)
            dflow_output_artifacts[f.name] = dflow.OutputArtifact(path=Path(path))
            source.append(f'args[{repr(f.name)}] = {repr(path)}')
            source.append(f'os.makedirs(os.path.dirname(args[{repr(f.name)}]), exist_ok=True)')

    source.extend([
        '',
        f'args_file = {repr(args_file)}',
        f'script_path = {repr(script_path)}',
        'with open(args_file, "w") as fp:',
        '    json.dump(args, fp, indent=2)',
        'os.system(f"python {script_path}")',
    ])

    fn_str = [
        'import cloudpickle as cp',
        'import base64, json, bz2, os',
        '',
        '# deserialize function',
        f'__fn = {pickle_converts(py_fn)}',
        '',
        '# deserialize args type',
        f'__ArgsType = {pickle_converts(args_type)}',
        '',
        '# run the function',
        f'with open({repr(args_file)}, "r") as fp:',
        '    __args = __ArgsType(**json.load(fp))',
        '__ret = __fn(__args)',
        '',
        '# handle the return value',
        f'os.makedirs({repr(output_parameters_path)}, exist_ok=True)',
    ]

    for f in iter_python_step_return(return_type):
        path = os.path.join(output_parameters_path, f.name)
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

    return _PythonTemplate(source='\n'.join(source),
                           fn_str='\n'.join(fn_str),
                           dflow_input_parameters=dflow_input_parameters,
                           dflow_input_artifacts=dflow_input_artifacts,
                           dflow_output_parameters=dflow_output_parameters,
                           dflow_output_artifacts=dflow_output_artifacts)


class DFlowBuilder:
    """
    A type friendly wrapper to build a DFlow workflow.
    """

    def __init__(self, name:str, s3_prefix: str, base_dir: str = '/tmp/dflow-builder', debug=False):
        """
        :param name: The name of the workflow.
        :param s3_prefix: The base prefix of the S3 bucket to store data generated by the workflow.
        :param base_dir: The base directory to mapping resources in remote container.
        :param debug: If True, the workflow will be run in debug mode.
        """
        if debug:
            dflow.config['mode'] = 'debug'

        self.name: Final[str] = name
        self.s3_prefix: Final[str] = s3_prefix
        self.base_dir: Final[str] = base_dir
        self.workflow: Final[dflow.Workflow] = dflow.Workflow(name=name)
        self._python_fns: Dict[Callable, str] = {}

    def s3_upload(self, path: os.PathLike, *keys: str, debug_func = None) -> str:
        """
        upload local file to S3.

        :param path: The local file path.
        :param keys: The keys of the S3 object.
        :param debug_func: The function to copy the file to the debug directory.
        """
        key = self._s3_get_key(*keys)
        return dflow.upload_s3(path, key, debug_func=debug_func)

    def s3_dump(self, data: Union[bytes, str], *keys: str, debug_func = None) -> str:
        """
        Dump data to s3.

        :param data: The bytes to upload.
        :param keys: The keys of the S3 object.
        :param debug_func: The function to copy the file to the debug directory.
        """
        mode = 'wb' if isinstance(data, bytes) else 'w'
        with tempfile.NamedTemporaryFile(mode) as fp:
            fp.write(data)
            fp.flush()
            return self.s3_upload(Path(fp.name), *keys, debug_func=debug_func)

    def run(self):
        self.workflow.submit()
        self.workflow.wait()

    def add_python_step(self,
                        fn: Callable[[T_IN], T_OUT],
                        with_param: Any = None,
                        ) -> Callable[[T_IN], T_OUT]:
        template = self._create_python_template(fn)

        def wrapped_fn(in_params: T_IN):
            step = dflow.Step(
                name='python-step-' + template.name + '-' + str(uuid4()),
                template=template,
                with_param=with_param,
                parameters={
                }

            )

        return wrapped_fn


    def _create_python_template(self, fn: Callable):
        _template = python_build_template(fn, base_dir=self.base_dir)
        fn_hash = hashlib.sha256(_template.fn_str.encode()).hexdigest()
        dflow_template = ScriptOPTemplate(
            name='python-template' + fn_hash,
            command='python3',
            script=_template.source,
        )
        dflow_template.inputs.parameters = _template.dflow_input_parameters
        dflow_template.inputs.artifacts = _template.dflow_input_artifacts
        dflow_template.outputs.parameters = _template.dflow_output_parameters
        dflow_template.outputs.artifacts = _template.dflow_output_artifacts
        # upload python script to s3
        key = self._get_or_create_python_fn(fn, _template.fn_str, fn_hash)
        dflow_template.inputs.artifacts['__fn__'] = dflow.InputArtifact(
            source=dflow.S3Artifact(key=key),
        )
        return dflow_template

    def _get_or_create_python_fn(self, fn, fn_str: str, fn_hash: str):
        if fn not in self._python_fns:
            fn_prefix = self.s3_dump(fn_str, 'build-in/python/fn', fn_hash)
            self._python_fns[fn] = fn_prefix
        return self._python_fns[fn]

    def _s3_get_key(self, *keys: str):
        return os.path.join(self.s3_prefix, *keys)
