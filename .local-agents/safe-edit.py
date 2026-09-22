from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Callable, Iterable


class SafeEditError(ValueError):
    pass


def normalize_relative_path(raw_path: str) -> str:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise SafeEditError("path is required")
    candidate = raw_path.replace("\\", "/")
    windows_path = PureWindowsPath(candidate)
    if windows_path.is_absolute() or windows_path.drive or candidate.startswith("/"):
        raise SafeEditError(f"absolute paths are not allowed: {raw_path}")
    parts = candidate.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SafeEditError(f"path must be normalized and repository-relative: {raw_path}")
    return "/".join(parts)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_reparse_point(path: Path) -> bool:
    """Return true for symlinks and Windows junction/reparse-point entries."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


class SafeEditor:
    def __init__(
        self,
        repo_root: Path,
        *,
        allowed_modify: Iterable[str],
        allowed_create: Iterable[str],
        mutation_guard: Callable[[], None] | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.allowed_modify = {normalize_relative_path(path) for path in allowed_modify}
        self.allowed_create = {normalize_relative_path(path) for path in allowed_create}
        self.mutation_guard = mutation_guard

    def _assert_no_reparse_components(self, relative: str) -> None:
        current = self.repo_root
        for part in Path(relative).parts:
            current = current / part
            if is_reparse_point(current):
                raise SafeEditError(
                    f"path traverses a symlink, junction, or reparse point: {relative}"
                )

    def _assert_mutation_allowed(self) -> None:
        if self.mutation_guard is not None:
            self.mutation_guard()

    @staticmethod
    def _write_new_file(path: Path, output: bytes) -> None:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(output)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    @staticmethod
    def _atomic_replace(path: Path, output: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.local-worker-", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(output)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
            os.replace(temporary, path)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def resolve(self, raw_path: str) -> tuple[str, Path]:
        relative = normalize_relative_path(raw_path)
        self._assert_no_reparse_components(relative)
        resolved = (self.repo_root / Path(relative)).resolve()
        root_key = os.path.normcase(str(self.repo_root))
        path_key = os.path.normcase(str(resolved))
        try:
            common = os.path.commonpath((root_key, path_key))
        except ValueError as exc:
            raise SafeEditError(f"path is outside repository: {raw_path}") from exc
        if common != root_key:
            raise SafeEditError(f"path is outside repository: {raw_path}")
        return relative, resolved

    def read_bytes(self, raw_path: str) -> tuple[bytes, str]:
        _, path = self.resolve(raw_path)
        if not path.is_file():
            raise SafeEditError(f"file does not exist: {raw_path}")
        data = path.read_bytes()
        return data, sha256_bytes(data)

    def create(self, raw_path: str, content: str) -> dict[str, str]:
        self._assert_mutation_allowed()
        relative, path = self.resolve(raw_path)
        if relative not in self.allowed_create:
            raise SafeEditError(f"file is not authorized for creation: {relative}")
        if path.exists():
            raise SafeEditError(f"refusing to overwrite existing file: {relative}")
        if not isinstance(content, str):
            raise SafeEditError("create requires string field 'content'")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._assert_no_reparse_components(relative)
        output = content.encode("utf-8")
        try:
            self._write_new_file(path, output)
        except FileExistsError as exc:
            raise SafeEditError(f"refusing to overwrite existing file: {relative}") from exc
        return {"path": relative, "sha256": sha256_bytes(output), "operation": "created"}

    def replace(
        self,
        raw_path: str,
        find: str,
        replacement: str,
        expected_sha256: str,
    ) -> dict[str, str]:
        self._assert_mutation_allowed()
        relative, path = self.resolve(raw_path)
        if relative not in self.allowed_modify:
            raise SafeEditError(f"file is not authorized for modification: {relative}")
        if not path.is_file():
            raise SafeEditError(f"file does not exist: {relative}")
        if not isinstance(find, str) or not find:
            raise SafeEditError("replace requires non-empty string field 'find'")
        if not isinstance(replacement, str):
            raise SafeEditError("replace requires string field 'replace'")
        if not isinstance(expected_sha256, str) or not expected_sha256:
            raise SafeEditError("replace requires expected_sha256 from a current READ_FILE result")

        raw = path.read_bytes()
        current_sha256 = sha256_bytes(raw)
        if current_sha256 != expected_sha256:
            raise SafeEditError(
                f"file changed since it was read: {relative}; read it again before editing"
            )

        bom = raw.startswith(b"\xef\xbb\xbf")
        payload = raw[3:] if bom else raw
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SafeEditError(f"file is not UTF-8: {relative}") from exc

        newline = "\r\n" if "\r\n" in text else "\n"

        def normalize_newlines(value: str) -> str:
            return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)

        find = normalize_newlines(find)
        replacement = normalize_newlines(replacement)
        occurrences = text.count(find)
        if occurrences == 0:
            raise SafeEditError("target block was not found")
        if occurrences != 1:
            raise SafeEditError(
                f"target block occurs {occurrences} times; refusing ambiguous edit"
            )

        updated = text.replace(find, replacement, 1).encode("utf-8")
        output = (b"\xef\xbb\xbf" + updated) if bom else updated
        self._assert_no_reparse_components(relative)
        if sha256_bytes(path.read_bytes()) != current_sha256:
            raise SafeEditError(
                f"file changed during edit preparation: {relative}; read it again before editing"
            )
        self._atomic_replace(path, output)
        return {"path": relative, "sha256": sha256_bytes(output), "operation": "modified"}


def fail(message: str) -> None:
    print(f"SAFE_EDIT_ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    try:
        request = json.load(sys.stdin)
        root = Path(request.get("repo_root", Path.cwd()))
        editor = SafeEditor(
            root,
            allowed_modify=request.get("allowed_modify", []),
            allowed_create=request.get("allowed_create", []),
        )
        operation = request.get("operation")
        if operation == "create":
            result = editor.create(request.get("path"), request.get("content"))
        elif operation == "replace":
            result = editor.replace(
                request.get("path"),
                request.get("find"),
                request.get("replace"),
                request.get("expected_sha256"),
            )
        else:
            raise SafeEditError("operation must be 'create' or 'replace'")
    except (SafeEditError, OSError, TypeError) as exc:
        fail(str(exc))
    print(json.dumps({"status": "ok", **result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
