import json
from pathlib import Path

from typer.testing import CliRunner

from retrolibx.application import ConversionService
from retrolibx.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def retroarch_library(root: Path) -> Path:
    rom = root / "roms/game.gba"
    rom.parent.mkdir(parents=True)
    rom.write_bytes(b"rom")
    root.joinpath("playlists").mkdir()
    root.joinpath("playlists/Nintendo - Game Boy Advance.lpl").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "path": str(rom),
                        "label": "Game",
                        "core_path": "DETECT",
                        "core_name": "DETECT",
                        "crc32": "DETECT",
                        "db_name": "Nintendo - Game Boy Advance.lpl",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return root


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    source, target = retroarch_library(tmp_path / "source"), tmp_path / "target"
    result = ConversionService().convert(source, target, "rocknix", dry_run=True)
    assert result.plan.actionable_count > 0
    assert result.execution is None
    assert not target.exists()


def test_retroarch_to_rocknix_end_to_end(tmp_path: Path) -> None:
    source, target = retroarch_library(tmp_path / "source"), tmp_path / "target"
    result = ConversionService().convert(source, target, "rocknix")
    assert result.execution is not None
    assert target.joinpath("gba/game.gba").read_bytes() == b"rom"
    assert "<name>Game</name>" in target.joinpath("gba/gamelist.xml").read_text()


def test_cli_detect_json_and_dry_run(tmp_path: Path) -> None:
    source, target = retroarch_library(tmp_path / "source"), tmp_path / "target"
    detected = runner.invoke(app, ["detect", str(source), "--json"])
    assert detected.exit_code == 0
    assert json.loads(detected.stdout)[0]["format"] == "retroarch"
    result = runner.invoke(
        app, ["convert", str(source), "--to", "rocknix", "--output", str(target), "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.stdout
    assert not target.exists()
