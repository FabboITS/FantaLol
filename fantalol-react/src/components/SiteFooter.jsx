import { Box, Container, Typography } from '@mui/material';

export function SiteFooter() {
  return (
    <Box component="footer" className="site-footer">
      <Container maxWidth="xl" className="footer-inner">
        <Typography fontWeight={800}>FANTALEAGUE</Typography>
        <Typography variant="body2" color="text.secondary">
          A React learning project inspired by competitive League of Legends.
        </Typography>
        <Typography variant="caption" color="text.secondary">Not affiliated with Riot Games.</Typography>
      </Container>
    </Box>
  );
}
