import { useEffect, useMemo, useState } from 'react';
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, Container, Divider,
  Grid, LinearProgress, Tab, Tabs, Typography,
} from '@mui/material';
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded';
import BoltRoundedIcon from '@mui/icons-material/BoltRounded';
import CalendarMonthOutlinedIcon from '@mui/icons-material/CalendarMonthOutlined';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import Groups2OutlinedIcon from '@mui/icons-material/Groups2Outlined';
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined';
import { Link, useParams } from 'react-router-dom';
import { LoadingState } from '../components/LoadingState';
import { MetricCard } from '../components/MetricCard';
import { PlayerCard } from '../components/PlayerCard';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

const tabs = ['overview', 'teams', 'auction', 'matchdays'];

export function LeaguePage() {
  const { leagueId } = useParams();
  const { user } = useAuth();
  const [league, setLeague] = useState(null);
  const [fantasyTeams, setFantasyTeams] = useState([]);
  const [matchdays, setMatchdays] = useState([]);
  const [players, setPlayers] = useState([]);
  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getLeague(leagueId, user.username),
      api.getFantasyTeams(leagueId),
      api.getMatchdays(leagueId),
      api.getPlayers(),
    ])
      .then(([leagueData, teamData, dayData, playerData]) => {
        if (!active) return;
        setLeague(leagueData);
        setFantasyTeams(teamData);
        setMatchdays(dayData);
        setPlayers(playerData);
      })
      .catch((reason) => { if (active) setError(reason.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [leagueId, user.username]);

  const ranking = useMemo(
    () => [...fantasyTeams].sort((left, right) => Number(right.punti) - Number(left.punti)),
    [fantasyTeams],
  );
  const myTeam = fantasyTeams.find((team) => team.ownerUsername === user.username);

  const copyCode = async () => {
    await navigator.clipboard.writeText(league.codiceInvito);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  if (loading) return <Container maxWidth="xl" className="page-container"><LoadingState label="Preparing your arena…" /></Container>;
  if (error || !league) {
    return <Container maxWidth="md" className="page-container"><Alert severity="error">{error || 'League not found.'}</Alert></Container>;
  }

  return (
    <Container maxWidth="xl" className="page-container">
      <Button component={Link} to="/leagues" startIcon={<ArrowBackRoundedIcon />} className="back-button">All leagues</Button>
      <Box className="league-hero">
        <Box>
          <Typography className="eyebrow">PRIVATE LEAGUE · ADMIN {league.adminUsername}</Typography>
          <Typography variant="h2" component="h1">{league.nome}</Typography>
          <Box className="league-hero-meta">
            <Chip icon={<Groups2OutlinedIcon />} label={`${fantasyTeams.length} managers`} />
            <Chip
              icon={<BoltRoundedIcon />}
              label={league.auctionOpen ? 'Auction live' : 'Auction closed'}
              color={league.auctionOpen ? 'success' : 'default'}
            />
          </Box>
        </Box>
        <Button variant="outlined" endIcon={<ContentCopyRoundedIcon />} onClick={copyCode}>
          {copied ? 'Copied!' : league.codiceInvito}
        </Button>
      </Box>

      <Tabs value={tab} onChange={(_event, value) => setTab(value)} variant="scrollable" className="league-tabs">
        {tabs.map((item) => <Tab key={item} value={item} label={item} />)}
      </Tabs>

      {tab === 'overview' && (
        <>
          <Grid container spacing={3} className="metric-grid">
            <Grid item xs={12} sm={4}><MetricCard label="YOUR BUDGET" value={`${myTeam?.creditiResidui ?? '—'} CR`} detail={myTeam?.nome || 'Spectator mode'} /></Grid>
            <Grid item xs={12} sm={4}><MetricCard label="MATCHDAYS" value={matchdays.length} detail={`${matchdays.filter((day) => day.chiusa).length} completed`} /></Grid>
            <Grid item xs={12} sm={4}><MetricCard label="ROSTER" value={`${myTeam?.rosa?.length ?? 0}/${league.maxRosterSize || 10}`} detail="Players acquired" /></Grid>
          </Grid>
          <Card className="dashboard-card">
            <CardContent>
              <Box className="card-title-row">
                <Box><Typography className="eyebrow">CURRENT TABLE</Typography><Typography variant="h4">Fantasy ranking</Typography></Box>
                <Typography color="text.secondary">Updated after each closed matchday</Typography>
              </Box>
              <Box className="ranking-list">
                {ranking.map((team, index) => (
                  <Box className="ranking-row" key={team.id}>
                    <Typography className="rank-number">{String(index + 1).padStart(2, '0')}</Typography>
                    <Avatar>{team.nome[0]}</Avatar>
                    <Box><Typography fontWeight={800}>{team.nome}</Typography><Typography variant="caption" color="text.secondary">{team.ownerUsername}</Typography></Box>
                    <Typography className="ranking-score">{Number(team.punti).toFixed(1)} <span>pt</span></Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </>
      )}

      {tab === 'teams' && (
        <Grid container spacing={3}>
          {fantasyTeams.map((team) => (
            <Grid item xs={12} md={6} key={team.id}>
              <Card className="team-card">
                <CardContent>
                  <Box className="card-title-row">
                    <Box><Typography className="eyebrow">{team.ownerUsername}</Typography><Typography variant="h5">{team.nome}</Typography></Box>
                    <Typography variant="h5">{Number(team.punti).toFixed(1)} pt</Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">{team.creditiResidui} credits available</Typography>
                  <LinearProgress variant="determinate" value={Math.min(100, ((team.rosa?.length || 0) / (league.maxRosterSize || 10)) * 100)} />
                  <Box className="compact-roster">
                    {team.rosa?.length ? team.rosa.map((entry) => (
                      <Box key={entry.id}><span>{entry.ruolo}</span><strong>{entry.lecPlayerNickname}</strong><small>{entry.creditiSpesi} CR</small></Box>
                    )) : <Typography color="text.secondary">No players acquired yet.</Typography>}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {tab === 'auction' && (
        <>
          <Card className="auction-status-card">
            <CardContent>
              <Box><Typography className="eyebrow">LIVE MARKET</Typography><Typography variant="h4">{league.auctionOpen ? 'The auction is open' : 'Waiting for the manager'}</Typography></Box>
              <Box className="auction-pulse"><span />{league.auctionOpen ? 'LIVE' : 'OFFLINE'}</Box>
            </CardContent>
          </Card>
          <Typography variant="h4" className="subsection-title">Available players</Typography>
          <Grid container spacing={3}>
            {players.slice(0, 8).map((player) => (
              <Grid item xs={12} sm={6} md={3} key={player.id}><PlayerCard player={player} /></Grid>
            ))}
          </Grid>
          <Alert severity="info" className="feature-note">The React replica currently presents the market. Real-time bidding remains available through the original Spring auction endpoints.</Alert>
        </>
      )}

      {tab === 'matchdays' && (
        <Card className="dashboard-card">
          <CardContent>
            <Box className="card-title-row">
              <Box><Typography className="eyebrow">COMPETITION</Typography><Typography variant="h4">Matchdays</Typography></Box>
              <CalendarMonthOutlinedIcon color="primary" />
            </Box>
            <Divider />
            <Box className="matchday-list">
              {matchdays.map((day) => (
                <Box key={day.id}>
                  <Box className="matchday-icon"><Inventory2OutlinedIcon /></Box>
                  <Box><Typography fontWeight={800}>Matchday {day.numero}</Typography><Typography variant="body2" color="text.secondary">{day.descrizione} · {day.data}</Typography></Box>
                  <Chip label={day.chiusa ? 'Closed' : 'Open'} color={day.chiusa ? 'default' : 'success'} size="small" />
                </Box>
              ))}
              {!matchdays.length && <Typography color="text.secondary">No matchday has been scheduled.</Typography>}
            </Box>
          </CardContent>
        </Card>
      )}
    </Container>
  );
}
