import { useEffect, useState } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Container, Grid, Stack, Typography,
} from '@mui/material';
import ArrowForwardRoundedIcon from '@mui/icons-material/ArrowForwardRounded';
import AutoAwesomeOutlinedIcon from '@mui/icons-material/AutoAwesomeOutlined';
import Groups2OutlinedIcon from '@mui/icons-material/Groups2Outlined';
import SportsEsportsOutlinedIcon from '@mui/icons-material/SportsEsportsOutlined';
import EmojiEventsOutlinedIcon from '@mui/icons-material/EmojiEventsOutlined';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';

const steps = [
  { number: '01', title: 'Create a private league', copy: 'Invite friends with a unique code and choose the starting budget.' },
  { number: '02', title: 'Build your roster', copy: 'Nominate LEC stars and outbid your rivals in a live credit auction.' },
  { number: '03', title: 'Win each matchday', copy: 'Submit a five-player lineup and score from real competitive performances.' },
];

export function HomePage() {
  const { isAuthenticated } = useAuth();
  const [playerCount, setPlayerCount] = useState('—');

  useEffect(() => {
    let active = true;
    api.getPlayers().then((players) => {
      if (active) setPlayerCount(players.length);
    }).catch(() => {
      if (active) setPlayerCount('50+');
    });
    return () => { active = false; };
  }, []);

  return (
    <>
      <Box className="hero">
        <Container maxWidth="xl" className="hero-inner">
          <Box className="hero-copy">
            <Chip icon={<AutoAwesomeOutlinedIcon />} label="Fantasy LEC · Summer 2026" className="hero-chip" />
            <Typography variant="h1" component="h1">
              Draft the stars.<br /><span>Own the Rift.</span>
            </Typography>
            <Typography className="hero-lead">
              Build your dream LEC roster, challenge your friends and turn every kill, assist and win into fantasy points.
            </Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <Button
                size="large"
                variant="contained"
                endIcon={<ArrowForwardRoundedIcon />}
                component={Link}
                to={isAuthenticated ? '/leagues' : '/login'}
              >
                {isAuthenticated ? 'Open my leagues' : 'Start playing'}
              </Button>
              <Button size="large" variant="outlined" component={Link} to="/players">Explore players</Button>
            </Stack>
            <Box className="hero-stats">
              <Box><strong>{playerCount}</strong><span>Pro players</span></Box>
              <Box><strong>10</strong><span>LEC teams</span></Box>
              <Box><strong>5</strong><span>Roles</span></Box>
            </Box>
          </Box>
          <Box className="hero-visual" aria-label="Fantasy league preview">
            <Box className="orbit orbit-one" />
            <Box className="orbit orbit-two" />
            <Card className="floating-card main-player-card">
              <CardContent>
                <Typography className="eyebrow">MID · G2 ESPORTS</Typography>
                <Box className="hero-player">
                  <span>CA</span>
                  <img
                    src="/Player_immage/other/Caps_1.webp"
                    alt="Caps"
                    onLoad={(event) => { event.currentTarget.previousElementSibling.hidden = true; }}
                    onError={(event) => {
                      event.currentTarget.previousElementSibling.hidden = false;
                      event.currentTarget.hidden = true;
                    }}
                  />
                </Box>
                <Typography variant="h4">Caps</Typography>
                <Typography color="text.secondary">100 credits</Typography>
              </CardContent>
            </Card>
            <Card className="floating-card score-card">
              <EmojiEventsOutlinedIcon color="primary" />
              <Box><Typography variant="caption">MATCHDAY SCORE</Typography><Typography variant="h5">48.6 pt</Typography></Box>
            </Card>
            <Card className="floating-card bid-card">
              <Typography variant="caption">LIVE BID</Typography>
              <Typography variant="h5">10.0s</Typography>
            </Card>
          </Box>
        </Container>
      </Box>

      <Container maxWidth="xl" className="section-block" id="rules">
        <Box className="section-heading">
          <Box>
            <Typography className="eyebrow">THE GAME PLAN</Typography>
            <Typography variant="h2">Three moves. One champion.</Typography>
          </Box>
          <Typography color="text.secondary">Simple to learn, merciless to master.</Typography>
        </Box>
        <Grid container spacing={3}>
          {steps.map((step) => (
            <Grid item xs={12} md={4} key={step.number}>
              <Card className="step-card">
                <CardContent>
                  <Typography className="step-number">{step.number}</Typography>
                  <Typography variant="h5">{step.title}</Typography>
                  <Typography color="text.secondary">{step.copy}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      <Container maxWidth="xl" className="section-block">
        <Box className="feature-strip">
          <Box><SportsEsportsOutlinedIcon /><Typography variant="h5">Live auction</Typography><Typography color="text.secondary">Ten-second bids keep every pick tense.</Typography></Box>
          <Box><Groups2OutlinedIcon /><Typography variant="h5">Private leagues</Typography><Typography color="text.secondary">Play in groups of two to ten managers.</Typography></Box>
          <Box><EmojiEventsOutlinedIcon /><Typography variant="h5">Real scoring</Typography><Typography color="text.secondary">LEC statistics drive the leaderboard.</Typography></Box>
        </Box>
      </Container>
    </>
  );
}
