"""Tests for Contree sandbox backend (simulation mode)."""

from pqc_factory.sandbox.contree import ContreeSandboxBackend
from pqc_factory.sandbox.manager import SandboxManager, create_sandbox_backend


def test_contree_sim_create_fork_write():
    sb = ContreeSandboxBackend(api_key="dummy")
    assert not sb.is_live

    base = sb.create_base("base")
    assert base.startswith("contree-")
    sb.write_file(base, "hello.py", "print('hi')")
    assert sb.read_file(base, "hello.py") == "print('hi')"

    branch = sb.fork(base, "exp1")
    assert sb.read_file(branch, "hello.py") == "print('hi')"
    sb.write_file(branch, "hello.py", "print('branch')")
    assert sb.read_file(base, "hello.py") == "print('hi')"
    assert sb.read_file(branch, "hello.py") == "print('branch')"
    assert "hello.py" in sb.list_files(branch)

    code, out, err = sb.run_command(branch, "python -c 'print(1)'")
    assert code == 0

    sb.cleanup(branch)
    sb.cleanup(base)


def test_factory_modes():
    local = create_sandbox_backend(mode="local")
    assert type(local).__name__ == "LocalSandboxBackend"

    contree = create_sandbox_backend(mode="contree")
    assert type(contree).__name__ == "ContreeSandboxBackend"

    mgr = SandboxManager(mode="contree")
    assert mgr.is_contree
    base = mgr.create_base("x")
    mgr.write_file(base, "a.txt", "1")
    assert mgr.read_file(base, "a.txt") == "1"
    mgr.cleanup()
