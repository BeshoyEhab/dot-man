"""End-to-end git round-trip: real clone, push and pull over a bare remote.

The unit tests for ``GitManager`` use single repositories; this one wires up
two working copies and a bare remote so the remote code paths
(``set_remote`` → ``push`` → ``clone`` → ``pull``) are exercised for real.
"""

from git import Repo

from dot_man.core import GitManager


def _configure_user(repo: Repo) -> None:
    with repo.config_writer() as config:
        config.set_value("user", "name", "Tester")
        config.set_value("user", "email", "tester@example.com")


def test_clone_push_pull_roundtrip(tmp_path):
    """A commit made on a clone reaches the original after a pull."""
    remote_dir = tmp_path / "remote.git"
    Repo.init(remote_dir, bare=True)

    # --- First machine: create history and publish it. ---
    work_dir = tmp_path / "work"
    work = GitManager(work_dir)
    work.init()
    _configure_user(work.repo)

    (work_dir / "tracked.txt").write_text("v1")
    work.add_all()
    work.commit("add tracked file")

    work.set_remote(str(remote_dir))
    assert work.get_remote_url() == str(remote_dir)

    work.push()

    # Point the bare repo's HEAD at the pushed branch so a plain clone checks
    # out a working tree instead of an unborn HEAD.
    branch = work.current_branch()
    Repo(remote_dir).git.symbolic_ref("HEAD", f"refs/heads/{branch}")

    # --- Second machine: clone and commit. ---
    clone_dir = tmp_path / "clone"
    clone = Repo.clone_from(str(remote_dir), clone_dir, branch=branch)
    _configure_user(clone)

    assert (clone_dir / "tracked.txt").read_text() == "v1"

    (clone_dir / "tracked.txt").write_text("v2")
    clone.index.add(["tracked.txt"])
    clone.index.commit("update from clone")
    clone.remotes.origin.push(branch)

    # --- First machine: pull the clone's commit. ---
    work.pull(rebase=False)

    assert (work_dir / "tracked.txt").read_text() == "v2"
    assert work.current_branch() == branch
