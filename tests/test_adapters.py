import json
from pathlib import Path

from retrolibx.adapters.emulationstation.adapter import EmulationStationAdapter
from retrolibx.adapters.esde.adapter import ESDEAdapter
from retrolibx.adapters.pegasus.adapter import PegasusAdapter
from retrolibx.adapters.retroarch.adapter import RetroArchAdapter
from retrolibx.adapters.rocknix.adapter import RocknixAdapter
from retrolibx.core.options import ExportOptions, ImportOptions
from retrolibx.registry import SystemRegistry


def systems() -> SystemRegistry:
    return SystemRegistry.load()


def make_rom(path: Path, content: bytes = b"rom") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_retroarch_import_and_render(tmp_path: Path) -> None:
    root = tmp_path / "ra"
    rom = make_rom(root / "roms/Advance Wars.gba")
    root.joinpath("playlists").mkdir()
    root.joinpath("playlists/Nintendo - Game Boy Advance.lpl").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "path": str(rom),
                        "label": "Advance Wars",
                        "core_path": "/cores/mgba.so",
                        "core_name": "mGBA",
                        "crc32": "1234",
                        "db_name": "Nintendo - Game Boy Advance.lpl",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    box = make_rom(
        root / "thumbnails/Nintendo - Game Boy Advance/Named_Boxarts/Advance Wars.png", b"png"
    )
    adapter = RetroArchAdapter(systems())
    assert adapter.detect(root).confidence == 0.95
    library = adapter.import_library(root, ImportOptions()).library
    assert library.systems[0].id == "gba"
    assert library.systems[0].games[0].launch.core == "mGBA"  # type: ignore[union-attr]
    assert library.systems[0].games[0].media.box_front == box
    intent = adapter.render_library(library, tmp_path / "out", ExportOptions())
    assert any(item.destination.name.endswith(".lpl") for item in intent.texts)


def write_es(root: Path) -> Path:
    rom = make_rom(root / "gba/Advance Wars.gba")
    image = make_rom(root / "gba/images/Advance Wars.png", b"png")
    root.joinpath("gba/gamelist.xml").write_text(
        f"""<?xml version="1.0"?>
<gameList><game><path>./{rom.name}</path><name>Advance Wars</name><desc>Strategy</desc><image>./images/{image.name}</image><developer>Intelligent Systems</developer><genre>Strategy</genre><releasedate>20010910T000000</releasedate><players>1-4</players><favorite>true</favorite></game></gameList>""",
        encoding="utf-8",
    )
    return root


def test_emulationstation_roundtrip_intent(tmp_path: Path) -> None:
    root = write_es(tmp_path / "es")
    adapter = EmulationStationAdapter(systems())
    library = adapter.import_library(root, ImportOptions()).library
    game = library.systems[0].games[0]
    assert game.name == "Advance Wars"
    assert game.players_max == 4
    intent = adapter.render_library(library, tmp_path / "out", ExportOptions())
    xml = intent.texts[0].content
    assert "<name>Advance Wars</name>" in xml
    assert "<favorite>true</favorite>" in xml


def test_profile_detection(tmp_path: Path) -> None:
    rocknix = tmp_path / "rocknix"
    write_es(rocknix / "roms")
    assert RocknixAdapter.detect(rocknix).confidence == 0.9
    esde = tmp_path / "esde"
    write_es(esde)
    esde.joinpath("ES-DE").mkdir()
    assert ESDEAdapter.detect(esde).confidence == 0.92


def test_pegasus_import_and_render(tmp_path: Path) -> None:
    root = tmp_path / "pegasus/gba"
    make_rom(root / "Advance Wars.gba")
    root.joinpath("metadata.pegasus.txt").write_text(
        """collection: Game Boy Advance
shortname: gba
extension: gba

game: Advance Wars
file: Advance Wars.gba
developer: Intelligent Systems
genre: Strategy
players: 1-4
favorite: true
launch: retroarch {file.path}
""",
        encoding="utf-8",
    )
    adapter = PegasusAdapter(systems())
    assert adapter.detect(root).confidence == 0.96
    library = adapter.import_library(root, ImportOptions()).library
    game = library.systems[0].games[0]
    assert game.players_max == 4
    assert game.launch.command == "retroarch {file.path}"  # type: ignore[union-attr]
    intent = adapter.render_library(library, tmp_path / "out", ExportOptions())
    assert "game: Advance Wars" in intent.texts[0].content
