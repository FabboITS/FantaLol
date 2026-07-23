import { Box, CircularProgress, Typography } from '@mui/material';

export function LoadingState({ label = 'Loading the Rift…' }) {
  return (
    <Box className="loading-state" role="status">
      <CircularProgress size={34} />
      <Typography color="text.secondary">{label}</Typography>
    </Box>
  );
}
