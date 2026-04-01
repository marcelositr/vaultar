import os
from pathlib import Path

def validate_sources(sources):
    """Checks if all source paths exist and are accessible."""
    invalid_paths = []
    for source in sources:
        path = Path(source).expanduser().resolve()
        if not path.exists():
            invalid_paths.append(str(path))
    return invalid_paths

def validate_destination(dest_path):
    """Checks if the destination exists and is writable."""
    path = Path(dest_path).expanduser().resolve()
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            return False, f"Could not create destination directory: {path}"
    
    if not os.access(path, os.W_OK):
        return False, f"Destination directory is not writable: {path}"
    
    return True, ""

def validate_backup_not_overwrite(dest_path, filename):
    """Checks if the backup file already exists."""
    path = Path(dest_path).expanduser().resolve() / filename
    return not path.exists()
