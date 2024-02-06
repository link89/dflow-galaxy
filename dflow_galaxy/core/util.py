import os

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def ensure_dirname(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
