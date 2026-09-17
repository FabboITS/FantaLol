"""Task Celery e management command (equivalenti dei worker/seeder Spring)."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.models import Role, User
from ingest.models import SyncState
from ingest.tasks import enrich_leaguepedia, sync_pandascore
from leagues.models import AuctionStatus, RosterEntry
from leagues.tasks import finalize_expired_auctions
from lineups.models import LineupPeriod
from lineups.tasks import apply_due_lineup_windows
from teams.models import Competition, ProPlayer, ProTeam
from worlds.tasks import lock_due_stage_lineups

from .factories import (
    FantaTeamFactory,
    LeagueFactory,
    ProPlayerFactory,
    UserFactory,
    WorldsStageFactory,
)

pytestmark = pytest.mark.django_db


def test_finalize_expired_auctions_task_assigns_the_player():
    from leagues.models import AuctionSession

    league = LeagueFactory(auction_open=True, participant_count=2)
    team = FantaTeamFactory(league=league, crediti_residui=500)
    player = ProPlayerFactory(quotazione=60)
    auction = AuctionSession.objects.create(
        league=league, player=player, highest_bidder=team, current_bid=60,
        ends_at=timezone.now() - timedelta(seconds=1), status=AuctionStatus.ACTIVE)

    assert finalize_expired_auctions() == 1
    auction.refresh_from_db()
    assert auction.status == AuctionStatus.WON
    assert RosterEntry.objects.filter(fanta_team=team, player=player).exists()


def test_sync_pandascore_task_reports_skipped_without_a_token(settings):
    settings.PANDASCORE = {**settings.PANDASCORE, "API_TOKEN": ""}
    result = sync_pandascore()
    assert result["skipped"] == 1
    assert SyncState.objects.filter(provider="PANDASCORE").exists()


def test_enrich_leaguepedia_task_is_skipped_without_credentials(settings):
    settings.LEAGUEPEDIA = {**settings.LEAGUEPEDIA, "BOT_USERNAME": "", "BOT_PASSWORD": ""}
    result = enrich_leaguepedia()
    assert result["skipped"] == 1
    state = SyncState.objects.get(provider="LEAGUEPEDIA")
    assert "già arricchiti" in state.last_error


def test_apply_due_lineup_windows_closes_overlapping_periods():
    team = FantaTeamFactory(league=LeagueFactory(participant_count=2))
    player = ProPlayerFactory()
    now = timezone.now()
    older = LineupPeriod.objects.create(fanta_team=team, role=player.ruolo, player=player,
                                        valid_from=now - timedelta(days=14))
    newer = LineupPeriod.objects.create(fanta_team=team, role=player.ruolo,
                                        player=ProPlayerFactory(ruolo=player.ruolo),
                                        valid_from=now - timedelta(days=7))
    assert apply_due_lineup_windows() == 1
    older.refresh_from_db()
    newer.refresh_from_db()
    assert older.valid_to == newer.valid_from
    assert newer.valid_to is None


def test_lock_due_stage_lineups_task_locks_expired_stages():
    stage = WorldsStageFactory(lineup_deadline=timezone.now() - timedelta(minutes=5))
    assert lock_due_stage_lineups() == 1
    stage.refresh_from_db()
    assert stage.lineups_locked is True


# --- seed -----------------------------------------------------------------
def test_seed_base_data_creates_admin_and_lec_rosters():
    call_command("seed_base_data", stdout=StringIO())
    admin = User.objects.get(username="Natsu_Admin")
    assert admin.role == Role.ADMIN
    assert admin.is_global_admin is True
    assert ProTeam.objects.filter(competition=Competition.LEC).count() == 10
    assert ProPlayer.objects.filter(competition=Competition.LEC).count() == 50


def test_seed_base_data_is_idempotent():
    call_command("seed_base_data", stdout=StringIO())
    call_command("seed_base_data", stdout=StringIO())
    assert ProPlayer.objects.count() == 50
    assert User.objects.filter(username="Natsu_Admin").count() == 1


def test_seed_base_data_can_set_an_explicit_admin_password():
    call_command("seed_base_data", "--admin-password", "supersegreta", stdout=StringIO())
    admin = User.objects.get(username="Natsu_Admin")
    assert admin.check_password("supersegreta") is True


def test_seed_assigns_the_frontend_asset_paths():
    call_command("seed_base_data", stdout=StringIO())
    caps = ProPlayer.objects.get(nickname="Caps")
    assert caps.image_url == "/Player_immage/Mid/Caps.jpg"
    assert caps.team.logo_url == "/assets/team-logos/g2-esports.png"
    # I nickname con spazi usano l'underscore, come nel seeder Java.
    assert ProPlayer.objects.get(nickname="Hans Sama").image_url == \
        "/Player_immage/Adc/Hans_Sama.jpg"


def test_bcrypt_legacy_hashes_stay_verifiable():
    """Gli hash BCrypt di Spring devono restare utilizzabili da Django."""
    user = UserFactory(password="password123")
    assert user.password.startswith("bcrypt$")
    assert user.check_password("password123") is True
    assert user.check_password("sbagliata") is False
