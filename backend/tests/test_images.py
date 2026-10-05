"""Immagini di team e player: download idempotente con resize, import degli asset legacy."""

import io
import json
from pathlib import Path

import httpx
import pytest
import respx
from django.core.management import call_command
from PIL import Image

from apps.competitions.models import Competition
from apps.esports.images import import_legacy_assets, normalize_image, safe_name
from apps.esports.models import ProPlayer, ProTeam

from .factories import EditionFactory, PlayerFactory, RosterFactory, TeamFactory

pytestmark = pytest.mark.django_db


def png(size=(600, 400)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


def test_download_ridimensiona_e_salva_per_ruolo_in_modo_idempotente(media, capsys):
    edition = EditionFactory(competition=Competition.objects.get(code="LCK"))
    team = TeamFactory(name="Gen.G", slug="gen-g", image_url_light="https://cdn.test/gen.png")
    player = PlayerFactory(nickname="Chovy", image_url="https://cdn.test/chovy.webp")
    RosterFactory(edition=edition, team=team, player=player, role="MID")
    RosterFactory(edition=edition, team=team, player=PlayerFactory(nickname="NoPhoto"), role="TOP")
    with respx.mock(assert_all_called=False) as router:
        router.get("https://cdn.test/gen.png").respond(
            200, content=png(), headers={"content-type": "image/png", "etag": '"v1"'}
        )
        router.get("https://cdn.test/chovy.webp").respond(
            200, content=png((300, 300)), headers={"content-type": "image/webp"}
        )
        call_command("download_esports_images", competition="LCK")
        report = json.loads(capsys.readouterr().out)
        assert report["teams"]["downloaded"] == 1 and report["players"]["downloaded"] == 1
        assert report["players"]["missing"] == 1
        team.refresh_from_db()
        player.refresh_from_db()
        assert team.logo_file == "teams/gen-g.png" and team.logo_etag == '"v1"'
        assert player.image_file == "players/lck/mid/Chovy.webp"
        assert max(Image.open(Path(media) / team.logo_file).size) == 256
        assert team.logo_url == "/media/teams/gen-g.png"
        router.get("https://cdn.test/gen.png").respond(304)
        call_command("download_esports_images", competition="lck")
        second = json.loads(capsys.readouterr().out)
        assert second["teams"]["unchanged"] == 1 and second["players"]["unchanged"] == 1
        router.get("https://cdn.test/chovy.webp").respond(500)
        player.image_hash = ""
        player.save()
        call_command("download_esports_images", competition="LCK")
        assert json.loads(capsys.readouterr().out)["players"]["failed"]


def test_import_degli_asset_legacy(media, tmp_path):
    source = tmp_path / "frontend"
    (source / "assets" / "team-logos").mkdir(parents=True)
    (source / "Player_immage" / "Adc").mkdir(parents=True)
    (source / "assets" / "team-logos" / "g2-esports.png").write_bytes(png())
    (source / "assets" / "team-logos" / "ignoto.png").write_bytes(png())
    (source / "Player_immage" / "Adc" / "Hans_Sama.jpg").write_bytes(png())
    ProTeam.objects.create(name="G2 Esports", slug="g2-esports")
    ProPlayer.objects.create(nickname="Hans Sama")
    report = import_legacy_assets(source)
    assert report["teams"] == 1 and report["players"] == 1 and report["unmatched"] == ["ignoto.png"]
    assert ProPlayer.objects.get().image_file == "players/lec/adc/Hans_Sama.jpg"
    assert (Path(media) / "teams" / "g2-esports.png").exists()


def test_utility_immagini():
    assert safe_name("Hans Sama!") == "Hans_Sama"
    assert normalize_image(b"<svg/>", "svg") == b"<svg/>"
    assert normalize_image(b"not-an-image", "png") == b"not-an-image"
    assert max(Image.open(io.BytesIO(normalize_image(png((1000, 10)), "jpg"))).size) == 256


def test_media_servite_con_cache(media, api):
    (Path(media) / "teams").mkdir(parents=True)
    (Path(media) / "teams" / "x.png").write_bytes(png((10, 10)))
    response = api.get("/media/teams/x.png")
    assert response.status_code == 200 and response["Cache-Control"] == "public, max-age=86400"


def test_transport_iniettabile():
    edition = EditionFactory(competition=Competition.objects.get(code="LPL"))
    RosterFactory(edition=edition, team=TeamFactory(image_url_light="https://cdn.test/t.png"))
    transport = httpx.MockTransport(lambda request: httpx.Response(404))
    from apps.esports.images import download_images

    assert download_images("LPL", transport=transport)["teams"]["failed"]
