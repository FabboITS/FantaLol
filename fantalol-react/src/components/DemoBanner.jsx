import { Alert, Button } from '@mui/material';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import { isDemoMode, api } from '../services/api';

export function DemoBanner() {
  if (!isDemoMode) return null;
  const reset = () => {
    api.resetDemo();
    window.location.reload();
  };
  return (
    <Alert
      severity="info"
      icon={<ScienceOutlinedIcon fontSize="small" />}
      className="demo-banner"
      action={<Button color="inherit" size="small" onClick={reset}>Reset demo</Button>}
    >
      Demo mode · login with <strong>demo / demo123</strong>
    </Alert>
  );
}
