import shutil
from pathlib import Path


def clear():
    """Clear all research results and knowledge base data."""
    targets = [
        Path.cwd() / "log",
        Path.cwd() / "pickle_cache",
        Path.cwd() / "git_ignore_folder",
    ]
    files = [
        Path.cwd() / "graph.pkl",
        Path.cwd() / "prompt_cache.db",
    ]

    for target in targets:
        if target.exists():
            shutil.rmtree(target)
            print(f"Removed {target}")

    for f in files:
        if f.exists():
            f.unlink()
            print(f"Removed {f}")

    print("All research results and knowledge base cleared.")
