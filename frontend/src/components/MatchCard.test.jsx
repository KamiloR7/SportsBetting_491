import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import MatchCard from './MatchCard';
import { match, market, response } from '../test/fixtures';

const card = value => <MemoryRouter><MatchCard match={value} returnParams={new URLSearchParams('league=football&status=scheduled')} /></MemoryRouter>;

describe('SCRUM-226 MatchCard rendering and eligibility', () => {
  it('shows teams, loading state and the contextual details link', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(card(match));
    expect(screen.getByText(match.home_team_name)).toBeVisible();
    expect(screen.getByText(match.away_team_name)).toBeVisible();
    expect(screen.getByText('Loading model odds…')).toBeVisible();
    expect(screen.getByRole('link', { name: /View match/ })).toHaveAttribute('href', '/matches/901?league=football&status=scheduled');
  });
  it('enables picks only for an open future model-priced market', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([market])));
    render(card(match));
    expect(await screen.findByRole('button', { name: /HOME\s*Cincinnati Bengals\s*Pick →/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /Cincinnati Bengals\s*1\.60\s*Bet/ })).toBeEnabled();
  });
  it('shows the final score and replay link without fetching odds', () => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
    render(card({ ...match, status: 'final', home_score: 24, away_score: 17 }));
    expect(screen.getByText('24')).toBeVisible();
    expect(screen.getByText('17')).toBeVisible();
    expect(screen.getByRole('link', { name: /View result & replay/ })).toBeVisible();
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each([
    ['closed market', match, { ...market, is_open: false }],
    ['in-progress match', { ...match, status: 'in_progress' }, market],
    ['kickoff passed', { ...match, start_time: '2020-01-01T00:00:00Z' }, market],
    ['reconstructed prices', match, { ...market, odds_source: 'model_reconstructed' }],
  ])('prevents picks for %s', async (_name, game, prices) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([prices])));
    render(card(game));
    await waitFor(() => expect(screen.queryByText('Loading model odds…')).toBeNull());
    expect(screen.queryByRole('button', { name: /^HOME / })).toBeNull();
    expect(screen.queryByRole('button', { name: /Place a bet/ })).toBeNull();
  });
  it.each([[], [{ ...market, odds_source: 'legacy_demo' }]])('shows unavailable instead of an invented price', async data => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(data)));
    render(card(match));
    expect(await screen.findByText('Model odds unavailable')).toBeVisible();
    expect(screen.queryByRole('button', { name: /Bet \/ Parlay/ })).toBeNull();
  });
  it('handles a market-service failure without losing navigation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    render(card(match));
    expect(await screen.findByText('Model odds unavailable')).toBeVisible();
    expect(screen.getByRole('link', { name: /View match/ })).toBeVisible();
  });
  it('opens and closes the inline slip with keyboard-accessible controls', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    vi.spyOn(Element.prototype, 'scrollIntoView').mockImplementation(() => {});
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => response([market])));
    render(card(match));
    const trigger = await screen.findByRole('button', { name: /HOME\s*Cincinnati Bengals\s*Pick →/ });
    await userEvent.click(trigger);
    expect(await screen.findByLabelText('Stake in points')).toHaveValue(100);
    expect(screen.getByLabelText('Bet slip for this match')).toHaveFocus();
    await userEvent.click(screen.getByRole('button', { name: 'Close bet slip' }));
    expect(screen.queryByLabelText('Stake in points')).toBeNull();
    expect(trigger).toHaveFocus();
  });
  it('does not offer the previous match price when a card receives another match', async () => {
    let finish;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response([market])).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })));
    const { rerender } = render(card(match));
    await screen.findByRole('button', { name: /Cincinnati Bengals\s*1\.60\s*Bet/ });
    rerender(card({ ...match, id: 902, home_team_name: 'New team' }));
    expect(screen.queryByRole('button', { name: /New team\s*1\.60\s*Bet/ })).toBeNull();
    await act(async () => finish(response([])));
    expect(await screen.findByText('Model odds unavailable')).toBeVisible();
  });
});
