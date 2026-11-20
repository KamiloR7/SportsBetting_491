// Synthetic UI fixtures. These values are not live sports/model evidence.
export const match = {
  id: 901, league_id: 1, league_name: 'National Football League',
  home_team_id: 1, away_team_id: 2,
  home_team_name: 'Cincinnati Bengals', away_team_name: 'Kansas City Chiefs',
  start_time: '2099-01-10T20:00:00Z', status: 'scheduled',
  home_score: null, away_score: null, neutral_site: false,
};
export const market = {
  market_id: 1, is_open: true, odds_source: 'model_derived', pricing_margin: 0.05,
  quoted_at: '2026-11-19T20:00:00Z', probabilities: { home: 0.6, away: 0.4 },
  outcomes: [{ id: 11, selection: 'home', decimal_odds: '1.60' },
    { id: 12, selection: 'away', decimal_odds: '2.40' }],
};
export const prediction = {
  match_id: 901, model_version: 'synthetic-ui-test', sport: 'NFL',
  home_team_name: match.home_team_name, away_team_name: match.away_team_name,
  predicted_outcome: 'HOME_WIN', confidence: 0.6,
  probabilities: { home_win: 0.6, not_home_win: 0.4 },
  history: { home_games: 12, away_games: 15 },
};
export const response = (body, status = 200) => new Response(JSON.stringify(body), { status });
