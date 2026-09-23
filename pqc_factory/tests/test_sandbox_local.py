from pqc_factory.sandbox.manager import SandboxManager


def test_fork_and_write():
    sm = SandboxManager(root="./.test_sandboxes")
    base = sm.create_base("testbase")
    sm.write_file(base, "hello.txt", "world")
    branch = sm.fork(base, "exp1")
    assert sm.read_file(branch, "hello.txt") == "world"
    sm.write_file(branch, "hello.txt", "changed")
    assert sm.read_file(base, "hello.txt") == "world"
    assert sm.read_file(branch, "hello.txt") == "changed"
    sm.cleanup()
