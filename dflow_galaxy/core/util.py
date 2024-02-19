from ai2_kit.core.util import list_split
import os


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def ensure_dirname(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def select_chunk(in_list: list, n: int, i: int):
    assert 0 <= i < n, f'nth should be in range [0, {n})'
    return list_split(sorted(in_list), n)[i]



def bash_iter_file_lines(in_file: str, script: str):
    """
    Generate a bash snippet to iterate over lines of a file

    :param in_file: input file
    :param script: bash script to process each line
    """

    return f"""while IFS= read -r line; do

{script}

    """



def bash_select_chunk(in_file: str, n: int, i: int, out_file: str, python_cmd: str = 'python'):
    """
    Generate a bash snippet to chunk a file by non empty lines into n part and select the ith part

    :param in_file: input file
    :param n: number of chunks
    :param i: chunk index
    :param out_file: output file
    """
    assert 0 <= i < n, f'nth should be in range [0, {n})'

    return f"""
# generated by: bash_select_chunk({in_file}, {n}, {i}, {out_file})
{python_cmd} << EOF > {out_file}
import sys
with open('{in_file}', 'r') as f:
    lines = f.readlines()
lines = [line for line in lines if line.strip()]
n, i = {n}, {i}
chunk_size = max(1, len(lines) // n)

start = i * chunk_size
end = (i + 1) * chunk_size if i < n - 1 else len(lines)
for line in lines[start:end]:
    sys.stdout.write(line)
EOF
# end of bash_select_chunk
    """.strip()
