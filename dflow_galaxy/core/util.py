from ai2_kit.core.util import list_split
import os


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def ensure_dirname(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def select_chunk(in_list: list, total_chunk: int, chunk_index: int):
    assert 0 <= chunk_index < total_chunk, f'chunk_index should be in range [0, {total_chunk})'
    return list_split(sorted(in_list), total_chunk)[chunk_index]
