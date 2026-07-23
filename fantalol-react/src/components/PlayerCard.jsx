import { Box, Card, CardContent, Chip, Typography } from '@mui/material';
import { roleColors } from '../data/demoData';

export function PlayerCard({ player }) {
  const roleColor = roleColors[player.ruolo] || '#8b5cf6';
  return (
    <Card className="player-card">
      <Box className="player-card-glow" sx={{ background: roleColor }} />
      <CardContent>
        <Box className="player-card-top">
          <Chip
            label={player.ruolo}
            size="small"
            sx={{ color: roleColor, borderColor: `${roleColor}66` }}
            variant="outlined"
          />
          <Typography fontWeight={850}>{player.quotazione} CR</Typography>
        </Box>
        <Box className="player-avatar" sx={{ bgcolor: player.color || roleColor }}>
          <span>{player.nickname.slice(0, 2).toUpperCase()}</span>
          {player.imageUrl && (
            <img
              src={player.imageUrl}
              alt={`Portrait of ${player.nickname}`}
              loading="lazy"
              onLoad={(event) => { event.currentTarget.previousElementSibling.hidden = true; }}
              onError={(event) => {
                event.currentTarget.previousElementSibling.hidden = false;
                event.currentTarget.hidden = true;
              }}
            />
          )}
        </Box>
        <Typography variant="h5" component="h2" fontWeight={800}>{player.nickname}</Typography>
        <Typography color="text.secondary">{player.teamNome}</Typography>
        <Box className="player-meta">
          <Typography variant="caption">{player.nazionalita || 'LEC'}</Typography>
          <Typography variant="caption" fontWeight={800}>{player.teamSigla || 'LEC'}</Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
