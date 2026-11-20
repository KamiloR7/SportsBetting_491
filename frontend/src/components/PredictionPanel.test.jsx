import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import PredictionPanel from './PredictionPanel';
import { prediction, response } from '../test/fixtures';

describe('SCRUM-226/227 PredictionPanel', () => {
  it('announces loading and prevents repeat requests while pending', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<PredictionPanel matchId={901} />);
    expect(screen.getByRole('status')).toHaveTextContent('Analyzing');
    expect(screen.getByRole('button', { name: 'Loading forecast…' })).toBeDisabled();
  });
  it('renders the forecast, probability meter and sample sizes from the API', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(prediction)));
    render(<PredictionPanel matchId={901} />);
    expect(await screen.findByText('Cincinnati Bengals favored')).toBeVisible();
    expect(screen.getByRole('meter')).toHaveAttribute('value', '0.6');
    expect(screen.getByText('History: 12 home-team games · 15 away-team games')).toBeVisible();
    expect(screen.getByRole('button', { name: 'Refresh insight' })).toBeEnabled();
  });
  it('shows EPL draw as an explicit leading outcome for three-way predictions', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ ...prediction, sport: 'EPL', home_team_name: 'Arsenal', away_team_name: 'Chelsea', probabilities: { home_win: 0.2, not_home_win: 0.8 }, confidence: 0.5, outcome_probabilities: { home: 0.2, draw: 0.5, away: 0.3 } })));
    render(<PredictionPanel matchId={901} />);
    expect(await screen.findByText('Draw is the leading outcome')).toBeVisible();
    expect(screen.getByText('Draw', { exact: true })).toHaveTextContent('Draw50%');
  });
  it.each([true, false])('labels historical replay and its correctness (%s)', async correct => {
    const fetch = vi.fn().mockResolvedValue(response({ ...prediction, correct, home_score: 24, away_score: 17, training_games: 200, training_end: '2026-01-01' }));
    vi.stubGlobal('fetch', fetch);
    render(<PredictionPanel matchId={901} replay />);
    expect(await screen.findByText(correct ? 'Prediction matched the result' : 'Prediction missed the result')).toBeVisible();
    expect(fetch.mock.calls[0][0]).toBe('/api/predictions/replay');
    expect(screen.getByText(/Target result excluded/)).toBeVisible();
  });
  it('shows a service error and allows a successful retry', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response({ detail: 'Insufficient prior history.' }, 422)).mockResolvedValueOnce(response(prediction)));
    render(<PredictionPanel matchId={901} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Insufficient prior history.');
    await userEvent.click(screen.getByRole('button', { name: 'Refresh insight' }));
    expect(await screen.findByText('Cincinnati Bengals favored')).toBeVisible();
    expect(screen.queryByRole('alert')).toBeNull();
  });
  it('keeps a prediction visible if browser storage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('quota'); });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(prediction)));
    render(<PredictionPanel matchId={901} />);
    expect(await screen.findByText('Cincinnati Bengals favored')).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('history could not be saved');
  });
  it('aborts an old request and ignores its late response after changing matches', async () => {
    let finish;
    const fetch = vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce(response({ ...prediction, home_team_name: 'New team' }));
    vi.stubGlobal('fetch', fetch);
    const { rerender } = render(<PredictionPanel matchId={901} />);
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    const signal = fetch.mock.calls[0][1].signal;
    rerender(<PredictionPanel matchId={902} />);
    expect(await screen.findByText('New team favored')).toBeVisible();
    expect(signal.aborted).toBe(true);
    await act(async () => finish(response(prediction)));
    expect(screen.queryByText('Cincinnati Bengals favored')).toBeNull();
  });
});
