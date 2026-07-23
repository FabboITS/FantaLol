import { render, screen } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { describe, expect, it } from 'vitest';
import { PlayerCard } from './PlayerCard';

const player = {
  id: 3,
  nickname: 'Caps',
  ruolo: 'MID',
  teamNome: 'G2 Esports',
  teamSigla: 'G2',
  nazionalita: 'Denmark',
  quotazione: 100,
};

describe('PlayerCard', () => {
  it('shows the player identity, role and auction price', () => {
    render(
      <ThemeProvider theme={createTheme()}>
        <PlayerCard player={player} />
      </ThemeProvider>,
    );

    expect(screen.getByRole('heading', { name: 'Caps' })).toBeInTheDocument();
    expect(screen.getByText('MID')).toBeInTheDocument();
    expect(screen.getByText('100 CR')).toBeInTheDocument();
    expect(screen.getByText('G2 Esports')).toBeInTheDocument();
  });
});
