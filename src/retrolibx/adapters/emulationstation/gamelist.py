"""Secure EmulationStation gamelist XML codec."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from lxml import etree

from retrolibx.core.models import Game, Media, Rom
from retrolibx.core.normalize import parse_bool, parse_date, parse_datetime, parse_players
from retrolibx.errors import ParseError

_KNOWN = {
    "path",
    "name",
    "sortname",
    "desc",
    "image",
    "thumbnail",
    "marquee",
    "video",
    "manual",
    "developer",
    "publisher",
    "genre",
    "releasedate",
    "players",
    "rating",
    "favorite",
    "hidden",
    "playcount",
    "lastplayed",
}


def _resolve(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve(strict=False)


def read_gamelist(path: Path) -> tuple[list[Game], list[str]]:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False)
    try:
        root = etree.parse(str(path), parser).getroot()
    except (OSError, etree.XMLSyntaxError) as exc:
        raise ParseError(f"Invalid gamelist XML {path}: {exc}") from exc
    if root.tag != "gameList":
        raise ParseError(f"Expected <gameList> root in {path}")
    games: list[Game] = []
    warnings: list[str] = []
    for index, node in enumerate(root.findall("game"), start=1):
        fields = {child.tag: child.text or "" for child in node if isinstance(child.tag, str)}
        raw_rom = fields.get("path")
        if not raw_rom:
            warnings.append(f"game #{index} has no path")
            continue
        rom = _resolve(path.parent, raw_rom)
        if rom is None:
            continue
        players_min, players_max = parse_players(fields.get("players"))
        try:
            rating = float(fields["rating"]) if fields.get("rating") else None
        except ValueError:
            rating = None
            warnings.append(f"{raw_rom}: invalid rating")
        if rating is not None:
            rating = min(1.0, max(0.0, rating))
        try:
            play_count = int(fields["playcount"]) if fields.get("playcount") else None
        except ValueError:
            play_count = None
        unknown = {key: value for key, value in fields.items() if key not in _KNOWN}
        games.append(
            Game(
                name=fields.get("name") or rom.stem,
                sort_name=fields.get("sortname") or None,
                roms=[Rom(path=rom, metadata={"source_path": raw_rom})],
                media=Media(
                    box_front=_resolve(path.parent, fields.get("image")),
                    screenshot=_resolve(path.parent, fields.get("thumbnail")),
                    marquee=_resolve(path.parent, fields.get("marquee")),
                    video=_resolve(path.parent, fields.get("video")),
                    manual=_resolve(path.parent, fields.get("manual")),
                ),
                description=fields.get("desc") or None,
                developer=fields.get("developer") or None,
                publisher=fields.get("publisher") or None,
                genre=[item.strip() for item in fields.get("genre", "").split(",") if item.strip()],
                release_date=parse_date(fields.get("releasedate")),
                players_min=players_min,
                players_max=players_max,
                rating=rating,
                favorite=parse_bool(fields.get("favorite")),
                hidden=parse_bool(fields.get("hidden")),
                play_count=play_count,
                last_played=parse_datetime(fields.get("lastplayed")),
                source_metadata={"emulationstation": unknown},
            )
        )
    return games, warnings


def _add(parent: etree._Element, tag: str, value: object | None) -> None:
    if value is None or value == "" or value == []:
        return
    node = etree.SubElement(parent, tag)
    if isinstance(value, bool):
        node.text = "true" if value else "false"
    elif isinstance(value, datetime):
        node.text = value.strftime("%Y%m%dT%H%M%S")
    elif isinstance(value, date):
        node.text = value.strftime("%Y%m%dT000000")
    else:
        node.text = str(value)


def write_gamelist(entries: list[tuple[Game, str, dict[str, str]]]) -> str:
    root = etree.Element("gameList")
    for game, rom_path, media_paths in entries:
        node = etree.SubElement(root, "game")
        _add(node, "path", rom_path)
        _add(node, "name", game.name)
        _add(node, "sortname", game.sort_name)
        _add(node, "desc", game.description)
        _add(node, "image", media_paths.get("box_front"))
        _add(node, "thumbnail", media_paths.get("screenshot"))
        _add(node, "marquee", media_paths.get("marquee") or media_paths.get("logo"))
        _add(node, "video", media_paths.get("video"))
        _add(node, "manual", media_paths.get("manual"))
        _add(node, "developer", game.developer)
        _add(node, "publisher", game.publisher)
        _add(node, "genre", ", ".join(game.genre))
        _add(node, "releasedate", game.release_date)
        players = None
        if game.players_min is not None:
            players = str(game.players_min)
            if game.players_max is not None and game.players_max != game.players_min:
                players += f"-{game.players_max}"
        _add(node, "players", players)
        _add(node, "rating", game.rating)
        _add(node, "favorite", game.favorite)
        _add(node, "hidden", game.hidden)
        _add(node, "playcount", game.play_count)
        _add(node, "lastplayed", game.last_played)
    xml = etree.tostring(root, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    return bytes(xml).decode("utf-8")
