"""Copie locali dei loghi dei team e delle foto dei player (fonte: PandaScore, piano gratuito).

* ``MEDIA_ROOT/teams/<slug>.<ext>``
* ``MEDIA_ROOT/players/<competizione>/<ruolo>/<nickname>.<ext>`` (cartelle per ruolo come ``Player_immage``)

Le immagini raster sono ridimensionate a massimo 256 px; il download è idempotente (ETag + hash SHA-256).
Non si scaricano immagini da Leaguepedia/Fandom (licenze dei file eterogenee).
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from django.conf import settings
from django.utils.text import slugify
from PIL import Image

from apps.competitions.models import Competition

from .models import EditionRoster, ProPlayer, ProTeam

logger = logging.getLogger(__name__)

MAX_SIZE = 256
CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "image/x-icon": "ico",
    "image/vnd.microsoft.icon": "ico",
    "image/gif": "gif",
}
LEGACY_ROLE_DIRS = {"Top": "TOP", "Jungle": "JUNGLE", "Mid": "MID", "Adc": "ADC", "Support": "SUPPORT"}


@dataclass
class ImageReport:
    downloaded: int = 0
    unchanged: int = 0
    missing: int = 0
    failed: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "downloaded": self.downloaded,
            "unchanged": self.unchanged,
            "missing": self.missing,
            "failed": self.failed,
        }


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "unknown"


def _extension(url: str, content_type: str | None) -> str:
    if content_type:
        ext = CONTENT_TYPES.get(content_type.split(";")[0].strip().lower())
        if ext:
            return ext
    suffix = Path(url.split("?")[0]).suffix.lower().lstrip(".")
    return {"jpeg": "jpg"}.get(suffix, suffix) or "png"


def normalize_image(content: bytes, ext: str) -> bytes:
    """Ridimensiona le immagini raster a max 256 px mantenendo il formato."""
    if ext in ("svg", "ico"):
        return content
    try:
        image = Image.open(io.BytesIO(content))
        image.thumbnail((MAX_SIZE, MAX_SIZE))
        output = io.BytesIO()
        fmt = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "gif": "GIF"}.get(ext, "PNG")
        if fmt == "JPEG" and image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(output, format=fmt)
        return output.getvalue()
    except Exception:  # immagine non decodificabile: si salva il file originale
        return content


def _store(relative: str, content: bytes) -> None:
    target = Path(settings.MEDIA_ROOT) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def _download(
    client: httpx.Client,
    url: str,
    etag: str,
    current_file: str,
    current_hash: str,
    relative_base: str,
    report: ImageReport,
):
    """Ritorna (file, hash, etag) aggiornati oppure ``None`` se invariato."""
    headers = {"If-None-Match": etag} if etag and current_file else {}
    response = client.get(url, headers=headers)
    if response.status_code == 304:
        report.unchanged += 1
        return None
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    if digest == current_hash and current_file and (Path(settings.MEDIA_ROOT) / current_file).exists():
        report.unchanged += 1
        return None
    ext = _extension(url, response.headers.get("content-type"))
    relative = f"{relative_base}.{ext}"
    _store(relative, normalize_image(response.content, ext))
    report.downloaded += 1
    return relative, digest, response.headers.get("etag", "")


def download_images(competition_code: str, transport: httpx.BaseTransport | None = None) -> dict:
    competition = Competition.objects.get(code__iexact=competition_code)
    editions = list(competition.active_editions()) or (
        [competition.current_edition()] if competition.current_edition() else []
    )
    entries = list(
        EditionRoster.objects.select_related("team", "player").filter(
            edition__in=editions, active_to__isnull=True
        )
    )
    teams = {e.team_id: e.team for e in entries}
    report = {"teams": ImageReport(), "players": ImageReport()}
    with httpx.Client(
        timeout=settings.HTTP_TIMEOUT_SECONDS, follow_redirects=True, transport=transport
    ) as client:
        for team in teams.values():
            _download_team(client, team, report["teams"])
        for entry in entries:
            _download_player(client, entry, competition.code.lower(), report["players"])
    return {kind: r.as_dict() for kind, r in report.items()}


def _download_team(client, team: ProTeam, report: ImageReport) -> None:
    url = team.image_url_light or team.image_url_dark
    if not url.startswith("http"):
        report.missing += 1
        return
    try:
        result = _download(
            client,
            url,
            team.logo_etag,
            team.logo_file,
            team.logo_hash,
            f"teams/{team.slug or slugify(team.name)}",
            report,
        )
    except httpx.HTTPError as error:
        report.failed.append(f"{team.name}: {error}")
        return
    if result:
        team.logo_file, team.logo_hash, team.logo_etag = result
        team.save(update_fields=["logo_file", "logo_hash", "logo_etag"])


def _download_player(client, entry: EditionRoster, code: str, report: ImageReport) -> None:
    player = entry.player
    if not player.image_url.startswith("http"):
        report.missing += 1
        return
    base = f"players/{code}/{entry.role.lower()}/{safe_name(player.nickname)}"
    try:
        result = _download(
            client, player.image_url, player.image_etag, player.image_file, player.image_hash, base, report
        )
    except httpx.HTTPError as error:
        report.failed.append(f"{player.nickname}: {error}")
        return
    if result:
        player.image_file, player.image_hash, player.image_etag = result
        player.save(update_fields=["image_file", "image_hash", "image_etag"])


def import_legacy_assets(source: Path | None = None) -> dict:
    """Copia in MEDIA_ROOT i loghi (assets/team-logos) e le foto per ruolo (Player_immage/<Ruolo>/) LEC."""
    source = Path(source or settings.FRONTEND_DIR)
    report = {"teams": 0, "players": 0, "unmatched": []}
    logos = source / "assets" / "team-logos"
    teams_by_slug = {}
    for team in ProTeam.objects.all():
        teams_by_slug[team.slug or slugify(team.name)] = team
        teams_by_slug[slugify(team.name)] = team
    if logos.exists():
        for path in sorted(logos.iterdir()):
            team = teams_by_slug.get(slugify(path.stem))
            if team is None:
                report["unmatched"].append(path.name)
                continue
            relative = f"teams/{team.slug or slugify(team.name)}{path.suffix.lower()}"
            content = path.read_bytes()
            _store(relative, normalize_image(content, path.suffix.lower().lstrip(".")))
            team.logo_file, team.logo_hash = relative, hashlib.sha256(content).hexdigest()
            team.save(update_fields=["logo_file", "logo_hash"])
            report["teams"] += 1
    photos = source / "Player_immage"
    for folder, role in LEGACY_ROLE_DIRS.items():
        directory = photos / folder
        if not directory.exists():
            continue
        for path in sorted(directory.iterdir()):
            nickname = path.stem.replace("_", " ")
            player = (
                ProPlayer.objects.filter(nickname__iexact=nickname).first()
                or ProPlayer.objects.filter(nickname__iexact=path.stem).first()
            )
            if player is None:
                report["unmatched"].append(f"{folder}/{path.name}")
                continue
            relative = f"players/lec/{role.lower()}/{safe_name(player.nickname)}{path.suffix.lower()}"
            target = Path(settings.MEDIA_ROOT) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            player.image_file = relative
            player.image_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            player.save(update_fields=["image_file", "image_hash"])
            report["players"] += 1
    return report
