from dflow.op_template import ScriptOPTemplate
import dflow

from typing import Final, Callable, TypeVar, Optional, Union, Annotated, Dict, get_type_hints
from dataclasses import dataclass, fields, is_dataclass
from collections import namedtuple
from enum import IntEnum, auto
from pathlib import Path
import cloudpickle as cp
import tempfile
import hashlib
import inspect
import base64
import shutil
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


def iter_python_step_input(obj):
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


def iter_python_step_output(obj):
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


_PythonStep = namedtuple('_PythonStep', ['source', 'script',
                                         'dflow_input_artifacts',
                                         'dflow_output_artifacts',
                                         'dflow_output_parameters'])


def build_python_step(py_fn: Callable,
                      args,
                      base_path: str) -> _PythonStep:
    """
    build a python step to run a python function.
    """
    sig = inspect.signature(py_fn)
    assert len(sig.parameters) == 1, f'{py_fn} should have only one parameter'
    args_type = sig.parameters[next(iter(sig.parameters))].annotation
    assert isinstance(args, args_type), f'{args} is not an instance of {args_type}'
    return_type  = sig.return_annotation

    args_file = os.path.join(base_path, 'tmp/args.json')
    script_path = os.path.join(base_path, 'tmp/script.py')
    output_parameters_path = os.path.join(base_path, 'output-parameters')

    dflow_input_artifacts: Dict[str, dflow.InputArtifact] = {}
    dflow_output_artifacts: Dict[str, dflow.OutputArtifact] = {}
    dflow_output_parameters: Dict[str, dflow.OutputParameter] = {}

    dflow_input_artifacts['__script__'] = dflow.InputArtifact(path=script_path)

    source = [
        'import os, json',
        '',
        'args = dict()',
    ]

    for f in iter_python_step_input(args):
        if f.type.__metadata__[0] == Symbol.INPUT_PARAMETER:
            # FIXME: may have error in some corner cases
            if issubclass(f.type.__origin__, str):
                val = f'"""{{{{inputs.parameters.{f.name}}}}}"""'
            else:
                val = f'json.loads("""{{{{inputs.parameters.{f.name}}}}}""")'
            source.append(f'args[{repr(f.name)}] = {val}')
        elif f.type.__metadata__[0] == Symbol.INPUT_ARTIFACT:
            path = os.path.join(base_path, 'input-artifacts', f.name)
            dflow_input_artifacts[f.name] = dflow.InputArtifact(path=path)
            source.append(f'args[{repr(f.name)}] = {repr(path)}')
        elif f.type.__metadata__[0] == Symbol.OUTPUT_ARTIFACT:
            path = os.path.join(base_path, 'output-artifacts', f.name)
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

    script = [
        'import cloudpickle as cp',
        'import base64, json, bz2, os',
        '',
        '# deserialize function',
        f'__fn = {pickle_converts(py_fn)}',
        '',
        '# deserialize args type',
        f'__ArgsType = {pickle_converts(type(args))}',
        '',
        '# run the function',
        f'with open({repr(args_file)}, "r") as fp:',
        '    __args = __ArgsType(**json.load(fp))',
        '__ret = __fn(__args)',
        '',
        '# handle the return value',
        f'os.makedirs({repr(output_parameters_path)}, exist_ok=True)',
    ]

    for f in iter_python_step_output(return_type):
        path = os.path.join(output_parameters_path, f.name)
        if issubclass(f.type.__origin__, str):
            script.extend([
                f'with open({repr(path)}, "w") as fp:',
                f'    fp.write(str(__ret.{f.name}))'
            ])
        else:
            script.extend([
                f'with open({repr(path)}, "w") as fp:',
                f'    json.dump(__ret.{f.name}, fp)'
            ])
        dflow_output_parameters[f.name] = dflow.OutputParameter(value_from_path=path)

    return _PythonStep(source='\n'.join(source),
                       script='\n'.join(script),
                       dflow_input_artifacts=dflow_input_artifacts,
                       dflow_output_artifacts=dflow_output_artifacts,
                       dflow_output_parameters=dflow_output_parameters)

class DFlowBuilder:
    """
    A type friendly wrapper to build a DFlow workflow.
    """

    def __init__(self, name:str, s3_prefix: str, debug=False):
        """
        :param name: The name of the workflow.
        :param s3_prefix: The base prefix of the S3 bucket to store data generated by the workflow.
        :param debug: If True, the workflow will be run in debug mode.
        """
        if debug:
            dflow.config['mode'] = 'debug'

        self.name: Final[str] = name
        self.s3_prefix: Final[str] = s3_prefix
        self.workflow = dflow.Workflow(name=name)

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
                        name: Optional[str] = None,
                        with_param=None,
                        mount_path: str = '/tmp/dflow',
                        ) -> Callable[[T_IN], T_OUT]:
        """
        Convert a python function to a DFlow step.

        1. Serialize the function and upload to S3.
        2. Build a template to run the function.
        3. Build a step to run the template.
        4. Add the step to the workflow.
        """

        def wrapped_fn(in_params: T_IN):
            build_python_step(fn, in_params, mount_path)




        return wrapped_fn


    def _s3_get_key(self, *keys: str):
        return os.path.join(self.s3_prefix, *keys)
