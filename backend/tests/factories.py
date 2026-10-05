"""Factory per i test (factory_boy)."""

from datetime import UTC, datetime

import factory

from apps.competitions.models import Competition, CompetitionEdition
from apps.esports.models import (
    EditionRoster,
    EsportsGame,
    EsportsMatch,
    EsportsMatchTeam,
    GamePlayerStat,
    ProPlayer,
    ProTeam,
)
from apps.leagues.models import FantaTeam, League, RosterEntry
from apps.users.models import Role, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@fantalol.test")
    role = Role.USER
    password = factory.PostGenerationMethodCall("set_password", "password123")

    @factory.post_generation
    def persist(obj, create, extracted, **kwargs):
        if create:
            obj.save()


class AdminFactory(UserFactory):
    role = Role.ADMIN


def competition(code: str = "LEC") -> Competition:
    return Competition.objects.get(code=code)


class EditionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompetitionEdition

    competition = factory.LazyFunction(lambda: Competition.objects.get(code="LEC"))
    year = 2026
    name = factory.Sequence(lambda n: f"Edizione {n}")
    starts_at = datetime(2026, 7, 24, tzinfo=UTC)
    ends_at = datetime(2026, 9, 30, tzinfo=UTC)
    is_active = True


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProTeam

    pandascore_id = factory.Sequence(lambda n: 1000 + n)
    name = factory.Sequence(lambda n: f"Team {n}")
    acronym = factory.Sequence(lambda n: f"T{n}")
    slug = factory.Sequence(lambda n: f"team-{n}")


class PlayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProPlayer

    pandascore_id = factory.Sequence(lambda n: 5000 + n)
    nickname = factory.Sequence(lambda n: f"Player{n}")


class RosterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EditionRoster

    edition = factory.SubFactory(EditionFactory)
    team = factory.SubFactory(TeamFactory)
    player = factory.SubFactory(PlayerFactory)
    role = "MID"
    quotazione = 10
    active_from = datetime(2026, 7, 24, tzinfo=UTC)


class LeagueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = League

    nome = factory.Sequence(lambda n: f"Lega {n}")
    crediti_iniziali = 1000
    admin = factory.SubFactory(UserFactory)
    edition = factory.SubFactory(EditionFactory)
    ruleset = factory.LazyAttribute(lambda o: o.edition.competition.ruleset)
    settings = factory.LazyFunction(dict)


class FantaTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FantaTeam

    nome = factory.Sequence(lambda n: f"FantaTeam {n}")
    crediti_residui = 1000
    league = factory.SubFactory(LeagueFactory)
    owner = factory.SubFactory(UserFactory)


class MatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EsportsMatch

    pandascore_id = factory.Sequence(lambda n: 90000 + n)
    edition = factory.SubFactory(EditionFactory)
    name = factory.Sequence(lambda n: f"Match {n}")
    status = "finished"
    begin_at = datetime(2026, 8, 1, 15, tzinfo=UTC)
    end_at = datetime(2026, 8, 1, 18, tzinfo=UTC)
    number_of_games = 3


def build_edition_rosters(edition, team_count: int = 10, price: int = 10) -> dict:
    """Crea ``team_count`` team con 5 player (uno per ruolo) nell'edizione."""
    teams = {}
    for index in range(team_count):
        team = TeamFactory(name=f"{edition.competition.code} Team {index}")
        teams[team] = [
            RosterFactory(
                edition=edition,
                team=team,
                role=role,
                quotazione=price + index,
                player=PlayerFactory(nickname=f"{team.acronym}-{role}"),
            )
            for role in ("TOP", "JUNGLE", "MID", "ADC", "SUPPORT")
        ]
    return teams


def add_match(
    edition,
    team_a,
    team_b,
    *,
    begin,
    winner=None,
    status="finished",
    stage=None,
    score=(1, 0),
    stats_complete=True,
):
    match = MatchFactory(
        edition=edition,
        begin_at=begin,
        end_at=begin,
        status=status,
        stage=stage,
        winner_team=winner,
        stats_complete=stats_complete,
        name=f"{team_a.name} vs {team_b.name}",
    )
    EsportsMatchTeam.objects.create(
        match=match, team=team_a, position=1, score=score[0], winner=winner == team_a
    )
    EsportsMatchTeam.objects.create(
        match=match, team=team_b, position=2, score=score[1], winner=winner == team_b
    )
    return match


def add_game(match, number=1, played_at=None, winner=None):
    return EsportsGame.objects.create(
        match=match,
        game_number=number,
        played_at=played_at or match.begin_at,
        leaguepedia_game_id=f"{match.pandascore_id}_{number}",
        winner_team=winner,
    )


def add_stat(game, player, *, kills=0, deaths=0, assists=0, cs=0, vision=0, win=False, team=None):
    return GamePlayerStat.objects.create(
        game=game,
        player=player,
        leaguepedia_link=player.nickname,
        kills=kills,
        deaths=deaths,
        assists=assists,
        cs=cs,
        vision_score=vision,
        win=win,
        team=team,
        is_complete=True,
    )


def give_roster(team: FantaTeam, entries, credits: int = 0):
    return [
        RosterEntry.objects.create(
            fanta_team=team, league=team.league, player=e.player, crediti_spesi=credits
        )
        for e in entries
    ]
