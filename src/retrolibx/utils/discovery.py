"""Repository-layout-independent metadata and referenced-file discovery."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

_IGNORED_DIRECTORIES = {".git", ".retrolibx", ".venv", "__pycache__"}


def find_metadata(path: Path, patterns: Iterable[str]) -> list[Path]:
    """Find metadata recursively, while accepting a metadata file directly."""
    pattern_set = tuple(patterns)
    if path.is_file():
        return [path] if any(path.match(pattern) for pattern in pattern_set) else []
    if not path.is_dir():
        return []
    found: set[Path] = set()
    for pattern in pattern_set:
        for candidate in path.rglob(pattern):
            if candidate.is_file() and not _ignored(candidate, path):
                found.add(candidate)
    return sorted(found)


def _ignored(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return any(part in _IGNORED_DIRECTORIES for part in relative.parts)


def _normalized_parts(path: str | Path) -> tuple[str, ...]:
    value = str(path).replace("\\", "/")
    return tuple(part.casefold() for part in value.split("/") if part not in {"", "."})


class FileIndex:
    """Index files once and resolve stale absolute or differently rooted references safely."""

    def __init__(self, root: Path, *, exclude: Iterable[Path] = ()) -> None:
        self.root = root.resolve(strict=False)
        excluded = {item.resolve(strict=False) for item in exclude}
        self._by_name: dict[str, list[Path]] = defaultdict(list)
        self._files: list[tuple[Path, tuple[str, ...]]] = []
        if not root.is_dir():
            return
        for candidate in root.rglob("*"):
            if not candidate.is_file() or _ignored(candidate, root):
                continue
            resolved = candidate.resolve(strict=False)
            if resolved in excluded:
                continue
            self._by_name[candidate.name.casefold()].append(resolved)
            self._files.append((resolved, _normalized_parts(candidate.relative_to(root))))

    def resolve(
        self,
        raw_path: str | Path,
        *,
        bases: Iterable[Path] = (),
        preferred_parts: Iterable[str] = (),
    ) -> Path | None:
        """Resolve without guessing when multiple candidates remain equally plausible."""
        source = Path(str(raw_path)).expanduser()
        direct = [source] if source.is_absolute() else []
        direct.extend(base / source for base in bases)
        direct.append(self.root / source)
        for candidate in direct:
            if candidate.is_file():
                return candidate.resolve()

        raw_parts = _normalized_parts(raw_path)
        # Stale device roots are common. Match the longest available trailing path first.
        for length in range(min(len(raw_parts), 6), 1, -1):
            suffix = raw_parts[-length:]
            matches = [path for path, parts in self._files if parts[-length:] == suffix]
            if len(matches) == 1:
                return matches[0]

        matches = list(self._by_name.get(source.name.casefold(), []))
        preferences = {item.casefold() for item in preferred_parts}
        if len(matches) > 1 and preferences:
            preferred = [
                match
                for match in matches
                if preferences.intersection(_normalized_parts(match.relative_to(self.root)))
            ]
            if len(preferred) == 1:
                return preferred[0]
        return matches[0] if len(matches) == 1 else None
