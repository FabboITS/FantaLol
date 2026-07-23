import { Box, Typography } from '@mui/material';

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <Box className="page-heading">
      <Box>
        <Typography className="eyebrow">{eyebrow}</Typography>
        <Typography variant="h2" component="h1">{title}</Typography>
        {description && <Typography color="text.secondary" className="page-description">{description}</Typography>}
      </Box>
      {action}
    </Box>
  );
}
