import os
import hashlib
from typing import Dict, Set

def _hash_file(path: str) -> str:
    """Compute lightweight hash of a file's contents."""
    try:
        with open(path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return "ERROR_READING_FILE"

def snapshot_state(scope_dir: str) -> Dict[str, str]:
    """
    Take a snapshot of the current state of files within the scope_dir.
    Returns a dictionary mapping file paths to their content hashes.
    """
    snapshot = {}
    if not os.path.exists(scope_dir) or not os.path.isdir(scope_dir):
        return snapshot

    for root, _, files in os.walk(scope_dir):
        # Skip common ignored directories
        if any(ignored in root.split(os.sep) for ignored in ['.git', 'node_modules', '__pycache__', 'venv', '.venv']):
            continue
            
        for name in files:
            file_path = os.path.join(root, name)
            snapshot[file_path] = _hash_file(file_path)
            
    return snapshot

def diff_state(before: Dict[str, str], after: Dict[str, str], expected_modifications: Set[str]) -> list:
    """
    Compare before and after states.
    Returns a list of anomalies (strings describing unexpected changes).
    expected_modifications should be absolute paths of files we EXPECT to change.
    """
    anomalies = []
    
    # Check for expected modifications that were made properly vs newly created files
    all_files = set(before.keys()).union(set(after.keys()))
    
    for file_path in all_files:
        hash_before = before.get(file_path)
        hash_after = after.get(file_path)
        
        if hash_before != hash_after:
            # File was changed, created, or deleted
            # Check if this change was in the expected_modifications set
            # Path formatting could differ, so we normalize
            norm_path = os.path.normpath(file_path)
            expected = any(os.path.normpath(e) == norm_path for e in expected_modifications)
            
            if not expected:
                if hash_before is None:
                    anomalies.append(f"UNEXPECTED_CREATION: {file_path}")
                elif hash_after is None:
                    anomalies.append(f"UNEXPECTED_DELETION: {file_path}")
                else:
                    anomalies.append(f"UNEXPECTED_MODIFICATION: {file_path}")
                    
    return anomalies
