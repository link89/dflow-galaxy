from typing import Optional, TypeVar
from ai2_kit.core.util import list_split
import shlex
import os


from .types import ListStr, SliceIndex

T = TypeVar('T')

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def ensure_dirname(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def not_none(v: Optional[T], msg: str = '') -> T:
    if v is None:
        raise ValueError(msg)
    return v


def ensure_str(s: ListStr):
    if isinstance(s, list):
        return '\n'.join(s)
    return s


def get_ln_cmd(from_path: str, to_path: str):
    """
    The reason to `rm -d` to_path is to workaround the limit of ln.
    `ln` command cannot override existed directory,
    so we need to ensure to_path is not existed.
    Here we use -d option instead of -rf to avoid remove directory with content.
    The error of `rm -d` is suppressed as it will fail when to_path is file.
    `-T` option of `ln` is used to avoid some unexpected result.
    """
    to_path = os.path.normpath(to_path)
    return 'rm -d {to_path} || true && ln -sfT {from_path} {to_path}'.format(
        from_path=shlex.quote(from_path),
        to_path=shlex.quote(to_path)
    )


def safe_ln(from_path: str, to_path: str, method=None):
    if method is None:
        method = os.system
    method(get_ln_cmd(from_path, to_path))


def select_chunk(in_list: list, n: int, i: int):
    assert 0 <= i < n, f'nth should be in range [0, {n})'
    return list_split(sorted(in_list), n)[i]


def bash_iter_ls_slice(search_pattern: str, /, n: int, i: SliceIndex, script: ListStr, opt: str = '',
                       it_var='ITEM', python_cmd: str = 'python'):
    """
    Generate a bash snippet to slice the result of `ls` command,
    and iterate over the selected chunk.

    :param search_pattern: search pattern for directories
    :param n: number of chunks
    :param i: chunk index
    :param script: bash script to process each directory
    :param it_var: variable name for each item
    """
    return '\n'.join([
        f'_LS_RESULT=$(ls -1 {opt} {search_pattern} | sort)',
        bash_slice(in_var='_LS_RESULT', n=n, i=i, out_var='_LS_CHUNK', python_cmd=python_cmd),
        bash_iter_var(in_var='_LS_CHUNK', script=script, it_var=it_var),
    ])


def bash_iter_var(in_var: str, script: ListStr, it_var='ITEM'):
    """
    Generate a bash snippet to iterate over lines of a variable

    :param in_var: variable name of input data
    :param script: bash script to process each line
    """
    script = ensure_str(script)
    return f"""while IFS= read -r {it_var}; do
{script}
done <<< "${in_var}" """


def bash_slice(in_var: str, n: int, i: SliceIndex, out_var: str,
               python_cmd: str = 'python'):
    """
    Generate a bash snippet to slice a multi-line string variable
    into n chunks and select the ith chunk

    :param in_var: variable name of input multi-line string
    :param n: number of chunks
    :param i: chunk index
    :param out_var: variable name to store the selected chunk
    """
    return f"""echo 'bash_slice({in_var}, {n}, {i}, {out_var})'
{out_var}=$(_IN_DATA="${in_var}" _SLICE_N={n} _SLICE_I={i} {python_cmd} << EOF
import sys,os
lines = os.environ['_IN_DATA'].split('\\n')
n = int(os.environ['_SLICE_N'])
i = int(os.environ['_SLICE_I'])
lines = [line for line in lines if line.strip()]
chunk_size = max(1, len(lines) // n)

start = i * chunk_size
end = (i + 1) * chunk_size if i < n - 1 else len(lines)
sys.stdout.write('\\n'.join(lines[start:end]))
EOF
)
echo 'bash_slice end' """
