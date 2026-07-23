import { Box, Button, Container, Typography } from '@mui/material';
import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <Container maxWidth="sm" className="not-found">
      <Box className="not-found-code">404</Box>
      <Typography variant="h3">This lane does not exist.</Typography>
      <Typography color="text.secondary">The page may have moved, or the Rift Herald ate the link.</Typography>
      <Button variant="contained" component={Link} to="/">Back to home</Button>
    </Container>
  );
}
