import { useCallback, useEffect, useState } from 'react';
import {
  Alert, Box, Button, Card, CardActionArea, CardContent, Container, Dialog,
  DialogActions, DialogContent, DialogTitle, Grid, Tab, Tabs, TextField, Typography,
} from '@mui/material';
import AddRoundedIcon from '@mui/icons-material/AddRounded';
import LoginRoundedIcon from '@mui/icons-material/LoginRounded';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/PageHeader';
import { LoadingState } from '../components/LoadingState';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export function LeaguesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [leagues, setLeagues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState('create');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const loadLeagues = useCallback(async () => {
    setLoading(true);
    try {
      setLeagues(await api.getLeagues(user.username));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  }, [user.username]);

  useEffect(() => { loadLeagues(); }, [loadLeagues]);

  const openDialog = (mode) => {
    setDialogMode(mode);
    setError('');
    setDialogOpen(true);
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const league = dialogMode === 'create'
        ? await api.createLeague(user.username, { nome: values.nome, creditiIniziali: Number(values.creditiIniziali) })
        : await api.joinLeague(user.username, values);
      setDialogOpen(false);
      await loadLeagues();
      navigate(`/leagues/${league.id}`);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Container maxWidth="xl" className="page-container">
      <PageHeader
        eyebrow="YOUR COMPETITIONS"
        title="My leagues."
        description="Create a private competition or join your friends with an invitation code."
        action={(
          <Box className="heading-actions">
            <Button variant="outlined" startIcon={<LoginRoundedIcon />} onClick={() => openDialog('join')}>Join</Button>
            <Button variant="contained" startIcon={<AddRoundedIcon />} onClick={() => openDialog('create')}>Create league</Button>
          </Box>
        )}
      />
      {loading && <LoadingState />}
      {!loading && (
        <Grid container spacing={3}>
          {leagues.map((league) => (
            <Grid item xs={12} md={6} lg={4} key={league.id}>
              <Card className="league-card">
                <CardActionArea onClick={() => navigate(`/leagues/${league.id}`)}>
                  <CardContent>
                    <Box className="league-card-top">
                      <Typography className="eyebrow">{league.numeroSquadre} MANAGERS</Typography>
                      <ArrowForwardRoundedIcon />
                    </Box>
                    <Typography variant="h4">{league.nome}</Typography>
                    <Typography color="text.secondary">Managed by {league.adminUsername}</Typography>
                    <Box className="league-code">
                      <span>INVITATION CODE</span><strong>{league.codiceInvito}</strong>
                    </Box>
                    <Box className="league-card-stats">
                      <span>{league.creditiIniziali} starting credits</span>
                      <span className={league.auctionOpen ? 'status-live' : ''}>{league.auctionOpen ? 'Auction live' : 'Pre-season'}</span>
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
          {!leagues.length && (
            <Grid item xs={12}>
              <Card className="empty-card">
                <CardContent>
                  <Typography variant="h5">Your trophy cabinet is empty.</Typography>
                  <Typography color="text.secondary">Create a league or ask a friend for an invitation code.</Typography>
                  <Button variant="contained" onClick={() => openDialog('create')}>Create the first league</Button>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{dialogMode === 'create' ? 'Start a new league' : 'Join a league'}</DialogTitle>
        <Tabs value={dialogMode} onChange={(_event, value) => { setDialogMode(value); setError(''); }} variant="fullWidth">
          <Tab label="Create" value="create" />
          <Tab label="Join" value="join" />
        </Tabs>
        <Box component="form" onSubmit={submit}>
          <DialogContent className="dialog-form">
            {error && <Alert severity="error">{error}</Alert>}
            {dialogMode === 'create' ? (
              <>
                <TextField name="nome" label="League name" required inputProps={{ maxLength: 100 }} />
                <TextField name="creditiIniziali" label="Starting credits" type="number" defaultValue={1000} required inputProps={{ min: 1 }} />
              </>
            ) : (
              <>
                <TextField name="codiceInvito" label="Invitation code" required />
                <TextField name="nomeSquadra" label="Fantasy team name" required />
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={saving}>{saving ? 'Saving…' : 'Continue'}</Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Container>
  );
}
