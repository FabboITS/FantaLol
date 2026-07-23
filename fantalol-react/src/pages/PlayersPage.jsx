import { useEffect, useMemo, useState } from 'react';
import {
  Alert, Box, Button, Container, Grid, InputAdornment, TextField,
} from '@mui/material';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import { PageHeader } from '../components/PageHeader';
import { PlayerCard } from '../components/PlayerCard';
import { LoadingState } from '../components/LoadingState';
import { api } from '../services/api';

const roles = ['ALL', 'TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

export function PlayersPage() {
  const [players, setPlayers] = useState([]);
  const [query, setQuery] = useState('');
  const [role, setRole] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api.getPlayers()
      .then((items) => { if (active) setPlayers(items); })
      .catch((reason) => { if (active) setError(reason.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const filteredPlayers = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return players.filter((player) => (
      (role === 'ALL' || player.ruolo === role)
      && (!normalized || `${player.nickname} ${player.teamNome} ${player.nazionalita}`.toLowerCase().includes(normalized))
    ));
  }, [players, query, role]);

  return (
    <Container maxWidth="xl" className="page-container">
      <PageHeader
        eyebrow="LEC SCOUTING"
        title="Find your next star."
        description="Compare roles and prices before your league auction begins."
      />
      <Box className="player-toolbar">
        <Box className="role-filters">
          {roles.map((item) => (
            <Button
              key={item}
              variant={role === item ? 'contained' : 'text'}
              onClick={() => setRole(item)}
              aria-pressed={role === item}
            >
              {item}
            </Button>
          ))}
        </Box>
        <TextField
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search player or team"
          size="small"
          InputProps={{ startAdornment: <InputAdornment position="start"><SearchRoundedIcon /></InputAdornment> }}
        />
      </Box>
      {loading && <LoadingState label="Scouting the LEC…" />}
      {error && <Alert severity="error">{error}</Alert>}
      {!loading && !error && (
        <Grid container spacing={3}>
          {filteredPlayers.map((player) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={player.id}>
              <PlayerCard player={player} />
            </Grid>
          ))}
          {!filteredPlayers.length && <Alert severity="info">No player matches these filters.</Alert>}
        </Grid>
      )}
    </Container>
  );
}
