import { match, market, prediction } from '../src/test/fixtures.js'

export async function mockApi(page, { listMode = 'normal' } = {}) {
  let authenticated = false
  const unexpected = []
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url()), path = url.pathname.replace(/^\/api/, '')
    let status = 200, data
    if (path === '/auth/me') { status = authenticated ? 200 : 401; data = authenticated ? { id: 1, email: 'synthetic-ui@example.com' } : { detail: 'Authentication required.' } }
    else if (path === '/auth/csrf') data = { csrf_token: 'synthetic-only-csrf' }
    else if (path === '/auth/register') { status = 201; data = { id: 1, email: 'synthetic-ui@example.com' } }
    else if (path === '/auth/login') {
      authenticated = route.request().postDataJSON().password === 'SyntheticUiOnly!'
      status = authenticated ? 200 : 401
      data = authenticated ? { id: 1, email: 'synthetic-ui@example.com' } : { detail: 'Invalid email or password.' }
    }
    else if (path === '/auth/logout') { authenticated = false; status = 204 }
    else if (path === '/wallet') data = { balance: 1000, currency: 'virtual_points' }
    else if (['/wallet/transactions', '/bets', '/parlays'].includes(path)) data = []
    else if (path === '/health') data = { status: 'ok', fixture_refresh: { enabled: false } }
    else if (path === '/leagues') data = [{ id: 1, abbreviation: 'NFL', name: 'National Football League' }, { id: 2, abbreviation: 'MLB', name: 'Major League Baseball' }, { id: 3, abbreviation: 'EPL', name: 'English Premier League' }]
    else if (path === '/matches') {
      if (listMode === 'error') { status = 503; data = { detail: 'Match data is unavailable.' } }
      else {
        const games = {
          '1': match,
          '2': { ...match, id: 902, league_id: 2, league_name: 'Major League Baseball', home_team_id: 3, away_team_id: 4, home_team_name: 'San Francisco Giants', away_team_name: 'Los Angeles Dodgers' },
          '3': { ...match, id: 903, league_id: 3, league_name: 'English Premier League', home_team_id: 5, away_team_id: 6, home_team_name: 'Arsenal', away_team_name: 'Chelsea' },
        }
        const game = games[url.searchParams.get('league_id')] || match
        const term = (url.searchParams.get('search') || '').toLowerCase()
        const matchesSearch = `${game.home_team_name} ${game.away_team_name}`.toLowerCase().includes(term)
        data = listMode === 'empty' || url.searchParams.get('view') === 'today_results' || !matchesSearch ? [] : [url.searchParams.get('status') === 'final' ? { ...game, id: game.id + 100, status: 'final', start_time: '2026-11-18T20:00:00Z', home_score: 24, away_score: 17 } : game]
      }
    }
    else if (path === '/matches/history') data = [{ ...match, id: 801, status: 'final', start_time: '2026-11-18T20:00:00Z', home_score: 24, away_score: 17 }]
    else if (path === '/matches/901') data = match
    else if (/^\/matches\/\d+\/markets$/.test(path)) data = [market]
    else if (path === '/predictions') data = prediction
    else if (path === '/insights/evaluation') data = { pricing_models: true, sports: ['NFL', 'MLB', 'EPL'].map(sport => ({ sport, accuracy: 0.6, baseline_accuracy: 0.5, test_rows: 10, classes: ['home', 'away'] })) }
    else if (path === '/insights/matches/901/inputs') { status = 503; data = { detail: 'Synthetic fixture has no stored history.' } }
    else { unexpected.push(path); status = 501; data = { detail: 'No UI fixture for this endpoint.' } }
    await route.fulfill({ status, contentType: 'application/json', body: status === 204 ? undefined : JSON.stringify(data) })
  })
  return unexpected
}

export async function evidence(page, testInfo, label) {
  const timestamp = new Date().toISOString()
  await page.evaluate(({ timestamp, label }) => {
    const banner = document.createElement('div')
    banner.id = 'qa-evidence-label'
    banner.textContent = `AUTOMATED UI TEST • MOCK API • ${label} • ${timestamp}`
    Object.assign(banner.style, { position: 'relative', zIndex: '2147483647', display: 'block', background: '#000', color: '#fff', font: '12px monospace', lineHeight: '1.5', padding: '8px', overflowWrap: 'anywhere' })
    document.body.prepend(banner)
  }, { timestamp, label })
  await page.screenshot({ path: testInfo.outputPath(`${label}.png`), fullPage: true })
  await page.evaluate(() => document.getElementById('qa-evidence-label')?.remove())
  await testInfo.attach(`${label}-timestamp`, { body: JSON.stringify({ timestamp, kind: 'automated browser; mock API', browser: testInfo.project.name }), contentType: 'application/json' })
}
