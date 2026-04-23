import os
import shutil
import tempfile
import pytest
from state_monitor import _hash_file, snapshot_state, diff_state

@pytest.fixture
def temp_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)

def test_hash_file_success(temp_dir):
    file_path = os.path.join(temp_dir, "test.txt")
    with open(file_path, "w") as f:
        f.write("hello world")

    # MD5 of "hello world" is 5eb63bbbe01eeed093cb22bb8f5acdc3
    assert _hash_file(file_path) == "5eb63bbbe01eeed093cb22bb8f5acdc3"

def test_hash_file_non_existent():
    assert _hash_file("non_existent_file.txt") == "ERROR_READING_FILE"

def test_hash_file_directory(temp_dir):
    assert _hash_file(temp_dir) == "ERROR_READING_FILE"

def test_snapshot_state_non_existent_dir():
    assert snapshot_state("/non/existent/path") == {}

def test_snapshot_state_success(temp_dir):
    file1 = os.path.join(temp_dir, "file1.txt")
    with open(file1, "w") as f:
        f.write("content1")

    os.makedirs(os.path.join(temp_dir, "subdir"))
    file2 = os.path.join(temp_dir, "subdir", "file2.txt")
    with open(file2, "w") as f:
        f.write("content2")

    snapshot = snapshot_state(temp_dir)
    assert len(snapshot) == 2
    assert file1 in snapshot
    assert file2 in snapshot
    assert snapshot[file1] == _hash_file(file1)
    assert snapshot[file2] == _hash_file(file2)

def test_diff_state():
    before = {
        "file1.txt": "hash1",
        "file2.txt": "hash2"
    }
    after = {
        "file1.txt": "hash1_mod",
        "file3.txt": "hash3"
    }
    # file1.txt: modified
    # file2.txt: deleted
    # file3.txt: created

    # 1. No expected modifications
    anomalies = diff_state(before, after, set())
    assert any("UNEXPECTED_MODIFICATION: file1.txt" in a for a in anomalies)
    assert any("UNEXPECTED_DELETION: file2.txt" in a for a in anomalies)
    assert any("UNEXPECTED_CREATION: file3.txt" in a for a in anomalies)
    assert len(anomalies) == 3

    # 2. file1.txt expected to change
    anomalies = diff_state(before, after, {"file1.txt"})
    assert not any("UNEXPECTED_MODIFICATION: file1.txt" in a for a in anomalies)
    assert any("UNEXPECTED_DELETION: file2.txt" in a for a in anomalies)
    assert any("UNEXPECTED_CREATION: file3.txt" in a for a in anomalies)
    assert len(anomalies) == 2
