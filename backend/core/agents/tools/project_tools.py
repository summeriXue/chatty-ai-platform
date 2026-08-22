from pathlib import Path

import difflib

import subprocess


def _resolve_project_path(project_root: str, relative_path: str) -> Path | None:
    """Resolve a project-relative path safely inside project_root."""

    root = Path(project_root).resolve()
    target = (root / relative_path).resolve()

    try:
        target.relative_to(root)
    except ValueError:
        return None

    return target


def read_project_file(project_root: str, relative_path: str) -> dict:
    """Read a UTF-8 text file inside the configured project root."""

    path = _resolve_project_path(project_root, relative_path)

    if path is None:
        return {"error": "Path is outside the project root"}

    if not path.exists():
        return {"error": f"File '{relative_path}' not found"}

    if not path.is_file():
        return {"error": f"'{relative_path}' is not a file"}

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": f"File '{relative_path}' is not a UTF-8 text file"}

    return {
        "path": relative_path,
        "content": content,
    }


def search_project_code(
    project_root: str,
    query: str,
    max_results: int = 50,
) -> dict:
    """Search text files inside the configured project root."""

    root = Path(project_root).resolve()

    if not root.exists() or not root.is_dir():
        return {"error": "Configured project root does not exist"}

    query = query.strip()
    if not query:
        return {"error": "Search query is required"}

    # Keep the first version conservative: skip large/generated/vendor dirs.
    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".next",
    }

    results: list[dict] = []

    for path in root.rglob("*"):
        if len(results) >= max_results:
            break

        if not path.is_file():
            continue

        try:
            relative = path.relative_to(root)
        except ValueError:
            continue

        if any(part in ignored_dirs for part in relative.parts):
            continue

        # Avoid binary / obviously irrelevant files in the first version.
        if path.suffix.lower() not in {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".json",
            ".md",
            ".yaml",
            ".yml",
            ".toml",
            ".txt",
            ".css",
            ".html",
            ".sql",
        }:
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(lines, start=1):
            if query.lower() not in line.lower():
                continue

            results.append({
                "path": str(relative),
                "line": line_number,
                "text": line.strip(),
            })

            if len(results) >= max_results:
                break

    return {
        "query": query,
        "results": results,
        "count": len(results),
        "truncated": len(results) >= max_results,
    }


def list_project_files(
    project_root: str,
    directory: str = "",
    max_entries: int = 200,
) -> dict:
    """List files and directories inside the configured project root."""

    root = Path(project_root).resolve()

    if not root.exists() or not root.is_dir():
        return {"error": "Configured project root does not exist"}

    relative_dir = directory.strip()

    target = (root / relative_dir).resolve()

    try:
        target.relative_to(root)
    except ValueError:
        return {"error": "Path is outside the project root"}

    if not target.exists():
        return {"error": f"Directory '{directory}' not found"}

    if not target.is_dir():
        return {"error": f"'{directory}' is not a directory"}

    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".next",
    }

    entries: list[dict] = []

    try:
        children = sorted(
            target.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )
    except OSError as e:
        return {"error": f"Failed to list directory: {e}"}

    for path in children:
        if len(entries) >= max_entries:
            break

        if path.name in ignored_dirs:
            continue

        try:
            relative = path.relative_to(root)
        except ValueError:
            continue

        entries.append({
            "path": str(relative),
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
        })

    return {
        "directory": relative_dir or ".",
        "entries": entries,
        "count": len(entries),
        "truncated": len(entries) >= max_entries,
    }


def preview_project_patch(
    project_root: str,
    relative_path: str,
    new_content: str,
) -> dict:
    """Preview a full-file replacement as a unified diff without writing."""

    path = _resolve_project_path(project_root, relative_path)

    if path is None:
        return {"error": "Path is outside the project root"}

    if not path.exists():
        return {"error": f"File '{relative_path}' not found"}

    if not path.is_file():
        return {"error": f"'{relative_path}' is not a file"}

    try:
        old_content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": f"File '{relative_path}' is not a UTF-8 text file"}

    diff = "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )

    return {
        "path": relative_path,
        "changed": old_content != new_content,
        "diff": diff,
        "new_content": new_content,
    }


def apply_project_patch(
    project_root: str,
    relative_path: str,
    new_content: str,
) -> dict:
    """Replace a project text file after path validation."""

    path = _resolve_project_path(project_root, relative_path)

    if path is None:
        return {"error": "Path is outside the project root"}

    if not path.exists():
        return {"error": f"File '{relative_path}' not found"}

    if not path.is_file():
        return {"error": f"'{relative_path}' is not a file"}

    try:
        old_content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": f"File '{relative_path}' is not a UTF-8 text file"}

    if old_content == new_content:
        return {
            "path": relative_path,
            "changed": False,
            "message": "No changes were necessary",
        }

    path.write_text(new_content, encoding="utf-8")

    return {
        "path": relative_path,
        "changed": True,
        "message": "File updated successfully",
    }


def git_project_status(project_root: str) -> dict:
    """Return the Git working-tree status for the configured project."""

    root = Path(project_root).resolve()

    if not root.exists() or not root.is_dir():
        return {"error": "Configured project root does not exist"}

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--short",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return {"error": "Git is not installed or not available on PATH"}
    except subprocess.TimeoutExpired:
        return {"error": "Git status timed out"}
    except OSError as e:
        return {"error": f"Failed to run Git: {e}"}

    if result.returncode != 0:
        return {
            "error": result.stderr.strip() or "git status failed",
            "returncode": result.returncode,
        }

    output = result.stdout.strip()

    return {
        "clean": not bool(output),
        "status": output,
    }


def git_project_diff(
    project_root: str,
    path: str = "",
) -> dict:
    """Return the unstaged Git diff for the configured project."""

    root = Path(project_root).resolve()

    if not root.exists() or not root.is_dir():
        return {"error": "Configured project root does not exist"}

    command = [
        "git",
        "-C",
        str(root),
        "diff",
        "--",
    ]

    if path.strip():
        target = (root / path.strip()).resolve()

        try:
            target.relative_to(root)
        except ValueError:
            return {"error": "Path is outside the project root"}

        command.append(path.strip())

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return {"error": "Git is not installed or not available on PATH"}
    except subprocess.TimeoutExpired:
        return {"error": "Git diff timed out"}
    except OSError as e:
        return {"error": f"Failed to run Git: {e}"}

    if result.returncode != 0:
        return {
            "error": result.stderr.strip() or "git diff failed",
            "returncode": result.returncode,
        }

    return {
        "path": path.strip() or None,
        "diff": result.stdout,
        "has_changes": bool(result.stdout.strip()),
    }
