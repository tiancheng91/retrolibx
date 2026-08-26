from pathlib import Path, PurePosixPath

import pytest

from retrolibx.core.executor import PlanExecutor
from retrolibx.core.operations import ExportIntent, FileRequest, TextRequest, TransferFile
from retrolibx.core.options import ConflictPolicy, ExportOptions, MediaMode, RomMode
from retrolibx.core.planner import ConversionPlanner
from retrolibx.errors import ConflictError, ValidationError


def make_plan(source: Path, target: Path, options: ExportOptions):
    rom = source / "game.gba"
    rom.parent.mkdir(parents=True, exist_ok=True)
    rom.write_bytes(b"rom")
    intent = ExportIntent(
        files=[FileRequest(source=rom, destination=PurePosixPath("gba/game.gba"), category="rom")],
        texts=[TextRequest(destination=PurePosixPath("gba/gamelist.xml"), content="<gameList/>\n")],
    )
    return ConversionPlanner().plan(
        intent,
        source_root=source,
        target_root=target,
        source_format="retroarch",
        target_format="rocknix",
        options=options,
    )


def test_plan_is_side_effect_free_and_execute_writes_manifest(tmp_path: Path) -> None:
    source, target = tmp_path / "source", tmp_path / "target"
    plan = make_plan(source, target, ExportOptions())
    assert not target.exists()
    report = PlanExecutor().execute(plan)
    assert (target / "gba/game.gba").read_bytes() == b"rom"
    assert (target / "gba/gamelist.xml").is_file()
    assert (target / ".retrolibx/manifest.json").is_file()
    assert source.joinpath("game.gba").is_file()
    assert report.completed


def test_same_root_rejected(tmp_path: Path) -> None:
    root = tmp_path / "same"
    root.mkdir()
    with pytest.raises(ValidationError):
        make_plan(root, root, ExportOptions())


def test_path_escape_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    rom = source / "game.gba"
    rom.write_bytes(b"rom")
    intent = ExportIntent(
        files=[FileRequest(source=rom, destination=PurePosixPath("../escape"), category="rom")]
    )
    with pytest.raises(ValidationError):
        ConversionPlanner().plan(
            intent,
            source_root=source,
            target_root=tmp_path / "target",
            source_format="a",
            target_format="b",
            options=ExportOptions(),
        )


@pytest.mark.parametrize(
    "policy",
    [ConflictPolicy.SKIP, ConflictPolicy.OVERWRITE, ConflictPolicy.RENAME, ConflictPolicy.NEWER],
)
def test_conflict_policies(tmp_path: Path, policy: ConflictPolicy) -> None:
    source, target = tmp_path / "source", tmp_path / "target"
    target.joinpath("gba").mkdir(parents=True)
    target.joinpath("gba/game.gba").write_bytes(b"old")
    plan = make_plan(source, target, ExportOptions(conflict=policy))
    transfer = next(op for op in plan.operations if isinstance(op, TransferFile))
    if policy == ConflictPolicy.SKIP:
        assert transfer.skipped
    elif policy in {ConflictPolicy.OVERWRITE, ConflictPolicy.NEWER}:
        assert transfer.overwrite
    else:
        assert transfer.destination.name == "game (2).gba"


def test_conflict_error(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.joinpath("gba").mkdir(parents=True)
    target.joinpath("gba/game.gba").write_bytes(b"old")
    with pytest.raises(ConflictError):
        make_plan(tmp_path / "source", target, ExportOptions(conflict=ConflictPolicy.ERROR))


@pytest.mark.parametrize("mode", [RomMode.COPY, RomMode.SYMLINK, RomMode.HARDLINK])
def test_file_modes(tmp_path: Path, mode: RomMode) -> None:
    source, target = tmp_path / mode.value / "source", tmp_path / mode.value / "target"
    plan = make_plan(source, target, ExportOptions(rom_mode=mode, media_mode=MediaMode.COPY))
    PlanExecutor().execute(plan)
    destination = target / "gba/game.gba"
    assert destination.read_bytes() == b"rom"
    if mode == RomMode.SYMLINK:
        assert destination.is_symlink()
