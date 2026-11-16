# Wallet activity and verified team branding

November 15, 2026. Wallet activity now describes where virtual points went or came from and links to the matching ticket. Team presentation now uses verified provider colors and real logos instead of generated colors.

## Wallet sources and destinations

GET /wallet/transactions retains its original ledger fields and adds title, source_label, description, ticket_type, ticket_id and ticket_status. A stake says To single bet #… or To 2-leg parlay #…; winning returns and refunds say From the associated ticket. Descriptions include the teams/picks, accepted odds and original stake. Payout text explicitly states that the return includes the original stake. Starting credits, custom refills and resets have distinct labels and no invented bet link.

The UI sends pending tickets to Active Bets and settled tickets to Bet History. Links include a stable single-{id}/parlay-{id} anchor; the matching card is focused, scrolled into view and highlighted. Enrichment is read-only, uses batched queries and applies the current user's ownership filter to both single and parlay lookups. A reference to someone else's ticket cannot expose its metadata.

Actual local proof: bet #1 backed Seattle for 100 points at its older accepted legacy price of 2.50. The provider final was Raiders 13–Seattle 21; the bet is WON and has exactly one +250 PAYOUT entry. At verification, the 778-point wallet equaled the sum of its ledger. Clicking From single bet #1 opened /bets/history#single-1. This is a genuine result-based local demo payout; it is separate from isolated synthetic tests used to verify model-priced returns and parlay outcomes.

## Verified team presentation

The committed presentation catalog has 130 provider profiles: 32 NFL, 30 MLB and 68 English clubs across current Premier League and supplemental Championship/League One directories. All 91 distinct league/team names used by the current imported matches resolve to a logo. Exact provider aliases handle Coventry/Hull, and the Oakland Athletics name maps to the same Athletics franchise. Ambiguous/unknown names receive no guessed identity.

The catalog stores source URLs, retrieval time, provider IDs, canonical names/aliases, primary/alternate hex colors and an ESPN-hosted logo URL. It stores no private data or image binaries. Current provider branding is used; old results are not claimed to have period-specific kit colors or historical logo versions. No database migration is required.

Cards and match-center badges load actual team logos from https://a.espncdn.com/i/teamlogos/. Colors are validated hex values; logo URLs are HTTPS and restricted to that host/path. Images use no-referrer, lazy loading and a neutral initials fallback if they fail. Unknown colors use a neutral palette. Very light colors get a darker surrounding tint for readable text. Team colors do not affect model features, prices or settlement.

To explicitly refresh metadata, from backend:

```powershell
python -m app.database.refresh_team_branding
```

Restart the backend to reload the cached catalog. This is separate from two-minute fixture updates: normal page loads never fetch the team directories. Team logos require internet access; no image can be guaranteed when the CDN is unreachable.

## Validation and evidence

Wallet/owner/reset checks: 13 passed, 1 skipped, including PostgreSQL variants. Branding/match/access-policy checks: 13 passed. Frontend build and lint passed. Browser checks confirmed NFL/MLB/EPL logos, match-center branding, readable payout/stake entries and the exact winning-ticket link.

Screenshots in docs/evidence: wallet-linked-payout.jpg, wallet-payout-linked-ticket.jpg, verified-nfl-team-logos.jpg, verified-epl-team-logos.jpg, verified-mlb-team-logos.jpg and verified-match-center-logos.jpg. Wallet-ticket highlighting was hardened to an explicit React class so it does not depend solely on browser :target behavior.
