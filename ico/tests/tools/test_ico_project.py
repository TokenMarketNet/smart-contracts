import sys

from ico.project import IcoProject


def test_ico_project_timeout():
    timeout = sys.maxsize
    project = IcoProject(timeout=timeout)
    with project.get_chain('tester') as chain:
        assert chain.wait.timeout == timeout
