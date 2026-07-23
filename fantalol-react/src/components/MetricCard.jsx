import { Card, CardContent, Typography } from '@mui/material';

export function MetricCard({ label, value, detail }) {
  return (
    <Card className="metric-card">
      <CardContent>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
        <Typography variant="h3">{value}</Typography>
        {detail && <Typography variant="body2" color="text.secondary">{detail}</Typography>}
      </CardContent>
    </Card>
  );
}
