# Summer 2026 Player Roster Corrections Design

## Goal

Correct the seeded Summer 2026 player roster, including player names, nationalities,
team assignments, and portrait URLs, while preserving every replaced player's
existing quotation.

## Roster Changes

| Role | Current player | Replacement or update | Team | Nationality | Quotation |
| --- | --- | --- | --- | --- | --- |
| Top | Empyros | Soboro | Fnatic | South Korea | Preserve Empyros value |
| Top | Lot | Oscarinin | GIANTX | Spain | Preserve Lot value |
| Jungle | Sheo | Team change only | Shifters | Preserve existing | Preserve existing |
| Jungle | Boukada | Daglas | Team Heretics | Poland | Preserve Boukada value |
| Mid | Humanoid | FIESTA | Team Vitality | South Korea | Preserve Humanoid value |
| Mid | LIDER | SlowQ | SK Gaming | South Korea | Preserve LIDER value |
| ADC | Noah | Flakked | GIANTX | Spain | Preserve Noah value |
| ADC | Ice | Hype | Team Heretics | South Korea | Preserve Ice value |
| Support | Stend | Team change only | Shifters | Preserve existing | Preserve existing |
| Support | Trymbi | Way | Team Heretics | South Korea | Preserve Trymbi value |

The stored nationality labels will follow the application's existing Italian
display vocabulary: `Corea del Sud`, `Spagna`, and `Polonia`.

## Architecture

`DataSeeder` remains the authoritative roster definition. Its clean-database seed
data will contain the corrected roster.

The existing-database path will run an idempotent roster synchronization before
asset metadata is refreshed. It will update existing `LecPlayer` entities in place
instead of deleting and recreating them. This preserves entity identifiers and
references from auction rosters, formations, and historical records.

Each correction identifies the existing player by nickname, changes only the
required nickname, nationality, and team, and leaves the quotation untouched.
Sheo and Stend retain their current nickname, nationality, and quotation while
moving to Shifters.

## Image Handling

Player portrait URLs continue to be derived from role and nickname:

`/Player_immage/{Role}/{Nickname}.jpg`

After roster synchronization, every affected player's image URL is refreshed.
The implementation will verify that all eight replacement portraits exist under
the expected frontend asset directories.

## Error Handling

Roster synchronization is idempotent. If an old nickname no longer exists but the
replacement already exists, the replacement is updated to the intended team and
nationality without creating a duplicate.

If an expected team is unavailable, synchronization will skip the affected
correction rather than assigning a player to the wrong team. Clean-database seeding
creates all teams before creating players.

## Testing

Tests will first describe and fail on the current implementation. They will verify:

- the clean seed roster contains all requested players and team assignments;
- replacement nationalities are correct;
- quotations remain equal to the replaced players' values;
- existing entities are updated in place and repeated synchronization is safe;
- Sheo and Stend move to Shifters;
- all new portrait paths resolve to existing static resources;
- obsolete roster entries are absent after synchronization.

Backend and frontend verification will run without Git commands.
