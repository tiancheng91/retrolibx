from pathlib import Path

from retrolibx.core.models import Game, Library, Rom, System
from retrolibx.core.normalize import normalized_filename, parse_date, parse_players
from retrolibx.registry import SystemRegistry


def test_mutable_model_defaults_are_isolated() -> None:
    first = Game(name="First")
    second = Game(name="Second")
    first.roms.append(Rom(path=Path("first.rom")))
    assert second.roms == []


def test_library_counts() -> None:
    library = Library(
        format="test",
        systems=[
            System(id="gba", name="GBA", games=[Game(name="A", roms=[Rom(path=Path("a.gba"))])])
        ],
    )
    assert library.game_count == 1
    assert library.media_count == 0


def test_registry_alias_and_directory() -> None:
    registry = SystemRegistry.load()
    assert registry.resolve("Nintendo - Game Boy Advance").id == "gba"  # type: ignore[union-attr]
    assert registry.resolve("GBA").id == "gba"  # type: ignore[union-attr]
    assert registry.directory("psx", "rocknix") == "psx"
    assert registry.resolve("unknown") is None


def test_normalizers() -> None:
    assert normalized_filename("Ninja (USA) [Rev 1].nes") == "ninja"
    assert parse_players("1-4") == (1, 4)
    assert parse_players("2") == (2, 2)
    assert parse_date("20010421T000000").isoformat() == "2001-04-21"  # type: ignore[union-attr]
