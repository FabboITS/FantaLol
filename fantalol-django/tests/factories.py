"""Factory condivise dalla suite (equivalente dei builder usati nei test JUnit)."""
from __future__ import annotations

from datetime import timedelta

import factory
from django.utils import timezone

from accounts.models import Role, User
from ingest.models import Game, GamePlayerStat, Match, MatchStatus
from leagues.models import FantaTeam, League, RosterEntry
from lineups.models import LineupPeriod
from teams.models import Competition, PlayerRole, ProPlayer, ProTeam
from worlds.models import WorldsEdition, WorldsLeague, WorldsStage, WorldsTeam


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@fantalol.test")
    role = Role.USER

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if create:
            self.set_password(extracted or "password123")
            self.save()


class AdminFactory(UserFactory):
    role = Role.ADMIN
    is_staff = True
    is_superuser = True


class ProTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProTeam

    nome = factory.Sequence(lambda n: f"Pro Team {n}")
    sigla = factory.Sequence(lambda n: f"PT{n}")
    competition = Competition.LEC


class ProPlayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProPlayer

    nickname = factory.Sequence(lambda n: f"Player{n}")
    ruolo = PlayerRole.MID
    quotazione = 50
    team = factory.SubFactory(ProTeamFactory)
    competition = Competition.LEC


class LeagueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = League

    nome = factory.Sequence(lambda n: f"Lega {n}")
    crediti_iniziali = 1000
    admin = factory.SubFactory(UserFactory)
    competition = Competition.LEC


class FantaTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FantaTeam

    nome = factory.Sequence(lambda n: f"Squadra {n}")
    crediti_residui = 1000
    league = factory.SubFactory(LeagueFactory)
    owner = factory.SubFactory(UserFactory)


class RosterEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RosterEntry

    fanta_team = factory.SubFactory(FantaTeamFactory)
    player = factory.SubFactory(ProPlayerFactory)
    crediti_spesi = 50


class LineupPeriodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LineupPeriod

    fanta_team = factory.SubFactory(FantaTeamFactory)
    player = factory.SubFactory(ProPlayerFactory)
    role = factory.LazyAttribute(lambda o: o.player.ruolo)
    valid_from = factory.LazyFunction(lambda: timezone.now() - timedelta(days=30))


class MatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Match

    pandascore_id = factory.Sequence(lambda n: 10_000 + n)
    name = factory.Sequence(lambda n: f"Serie {n}")
    league_code = "LEC"
    status = MatchStatus.FINISHED
    begin_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=1))
    end_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=20))
    opponents = factory.List(["Team A", "Team B"])


class GameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Game

    match = factory.SubFactory(MatchFactory)
    game_number = 1
    external_game_id = factory.Sequence(lambda n: f"GAME-{n}")
    played_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=22))


class GamePlayerStatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GamePlayerStat

    game = factory.SubFactory(GameFactory)
    player = factory.SubFactory(ProPlayerFactory)
    source_link = factory.LazyAttribute(lambda o: o.player.nickname)
    role = factory.LazyAttribute(lambda o: o.player.ruolo)


class WorldsEditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorldsEdition

    nome = factory.Sequence(lambda n: f"Worlds 20{26 + n}")
    anno = factory.Sequence(lambda n: 2026 + n)


class WorldsStageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorldsStage

    edition = factory.SubFactory(WorldsEditionFactory)
    nome = "Swiss"
    ordine = factory.Sequence(lambda n: n + 1)
    lineup_deadline = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))


class WorldsLeagueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorldsLeague

    nome = factory.Sequence(lambda n: f"Lega Worlds {n}")
    edition = factory.SubFactory(WorldsEditionFactory)
    admin = factory.SubFactory(UserFactory)
    crediti_iniziali = 500
    roster_size = 10
    max_per_role = 2


class WorldsTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorldsTeam

    nome = factory.Sequence(lambda n: f"Worlds Team {n}")
    league = factory.SubFactory(WorldsLeagueFactory)
    owner = factory.SubFactory(UserFactory)
    crediti_residui = 500
