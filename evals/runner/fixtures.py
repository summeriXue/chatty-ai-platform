"""Eval fixtures for creating isolated temporary Chatty agents.

Fixture provisioning intentionally uses Chatty's existing low-level agent
creation primitives instead of the public POST /api/agents route.

This avoids unrelated production-side effects such as onboarding pending
integration setup consumption and shared-knowledge bootstrap, while the actual
evaluated agent execution still goes through Chatty's normal HTTP /chat API.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

@dataclass
class ProjectStateSnapshot:
    """Filesystem snapshot of the project's pre-eval dirty state."""

    backup_dir: Path
    tracked_dirty: set[str]
    tracked_deleted: set[str]
    untracked_files: set[str]


def _run_git(*args: str) -> str:
    """Run a Git command against the Chatty project root."""

    completed = subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def _git_paths(*args: str) -> set[str]:
    """Return NUL-separated Git paths as normalized project-relative strings."""

    output = _run_git(*args)

    return {
        path.replace("\\", "/")
        for path in output.split("\0")
        if path
    }


def snapshot_project_state() -> ProjectStateSnapshot:
    """Capture the project's dirty working-tree state before a write eval."""

    tracked_dirty = _git_paths(
        "ls-files",
        "-m",
        "-z",
    )

    tracked_deleted = _git_paths(
        "ls-files",
        "-d",
        "-z",
    )

    untracked_files = _git_paths(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )

    backup_dir = Path(
        tempfile.mkdtemp(prefix="chatty-eval-project-")
    )

    paths_to_backup = (
        tracked_dirty
        | untracked_files
    ) - tracked_deleted

    try:
        for relative_path in paths_to_backup:
            source = PROJECT_ROOT / relative_path
            if not source.is_file():
                continue

            destination = backup_dir / relative_path
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            shutil.copy2(
                source,
                destination,
            )

        return ProjectStateSnapshot(
            backup_dir=backup_dir,
            tracked_dirty=tracked_dirty,
            tracked_deleted=tracked_deleted,
            untracked_files=untracked_files,
        )

    except Exception:
        shutil.rmtree(
            backup_dir,
            ignore_errors=True,
        )
        raise


def restore_project_state(
    snapshot: ProjectStateSnapshot,
) -> None:
    """Restore the exact pre-eval working-tree state."""

    try:
        current_tracked_dirty = _git_paths(
            "ls-files",
            "-m",
            "-z",
        )

        current_tracked_deleted = _git_paths(
            "ls-files",
            "-d",
            "-z",
        )

        tracked_changed_by_eval = (
            current_tracked_dirty
            | current_tracked_deleted
        )

        if tracked_changed_by_eval:
            subprocess.run(
                [
                    "git",
                    "restore",
                    "--worktree",
                    "--",
                    *sorted(tracked_changed_by_eval),
                ],
                cwd=PROJECT_ROOT,
                check=True,
            )

        current_untracked_files = _git_paths(
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        )

        eval_created_untracked = (
            current_untracked_files
            - snapshot.untracked_files
        )

        for relative_path in sorted(
            eval_created_untracked,
            reverse=True,
        ):
            path = PROJECT_ROOT / relative_path

            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)

        for relative_path in (
            snapshot.tracked_dirty
            | snapshot.untracked_files
        ):
            if relative_path in snapshot.tracked_deleted:
                continue

            backup = snapshot.backup_dir / relative_path
            if not backup.is_file():
                continue

            destination = PROJECT_ROOT / relative_path
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                backup,
                destination,
            )

        for relative_path in snapshot.tracked_deleted:
            path = PROJECT_ROOT / relative_path

            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)

    finally:
        shutil.rmtree(
            snapshot.backup_dir,
            ignore_errors=True,
        )

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from agents import db as agent_db
from agents.engine import DATA_DIR, invalidate_cache
from agents.presets import (
    TECHNICAL_ENGINEER_PERSONALITY,
    apply_agent_preset,
)
from agents.templates import seed_context_files


def create_tech_eval_agent(case_id: str) -> dict:
    """Create a fresh isolated Technical Engineer agent for one eval case."""

    agent_db.init_db()

    agent_name = f"Tech Eval {case_id}"

    agent = agent_db.create_agent(
        agent_name,
        personality=TECHNICAL_ENGINEER_PERSONALITY,
    )

    try:
        agent = agent_db.update_agent(
            agent["id"],
            project_root=str(PROJECT_ROOT),
        )

        context_dir = DATA_DIR / agent["slug"] / "context"

        seed_context_files(
            context_dir,
            agent["agent_name"],
        )

        apply_agent_preset(
            "technical_engineer",
            context_dir,
        )

        return agent

    except Exception:
        delete_tech_eval_agent(agent)
        raise


def delete_tech_eval_agent(agent: dict) -> None:
    """Delete a temporary eval agent and its agent-scoped data."""

    agent_id = agent["id"]
    slug = agent["slug"]

    agent_db.delete_agent(agent_id)
    invalidate_cache(slug)

    agent_dir = DATA_DIR / slug
    if agent_dir.exists():
        shutil.rmtree(agent_dir)
