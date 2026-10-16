# Historical match quality gate (DATA-24)

Use `src.normalizers.match_validation.validate_historical_matches(rows)` on
canonical match dictionaries before loading. Run raw provider records through
their sport adapter first. Returned accepted rows follow `MATCH_FIELDS`.

The report provides `accepted`, `rejected`, `duplicates`, and `counts`;
`to_dict()` returns these for logging or JSON reporting. Rejections identify
zero-based input indexes and explicit reasons. Inputs are not mutated.

Existing sport adapters enforce score, date, winner and season rules. The gate
adds canonical identity checks, sport/league consistency, database identifier
length limits, and whole-batch accounting. Duplicate identity is exactly
`(source, game_id)`, matching database external match mappings. Identical
normalized records keep the first occurrence. Conflicting valid records reject
every occurrence in their group, without choosing an arbitrary winner.
Invalid records are rejected independently before duplicate grouping.

`read = accepted + rejected + duplicates`. Conflicting groups contribute to
rejected, not duplicates. Duplicate entries identify the retained input index.

NFL ties retain no winning team and `TIE`; EPL draws retain outcome `DRAW`;
completed MLB ties are rejected. Optional supplied NFL outcome metadata is
checked against scores (`HOME_WIN`, `AWAY_WIN`, `TIE`). The NFL normalizer's
existing output metadata policy is preserved.

Acceptance means data-quality acceptance, not guaranteed PostgreSQL loading.
Date-only records remain valid; the current loader requires kickoff timestamps.
The loader also needs policy for `suspended`/`incomplete`, source/team reference
mapping, season/metadata persistence, and a transaction around match/mapping
writes. No database lookup or existing-database duplicate detection occurs here.

The Sprint 3 ML contract uses separate NBA/NFL/UEFA prediction labels and binary
NFL targets, while the historical contract uses official NFL/MLB/EPL identities
and preserves raw ties/draws. ML outcome/probability helpers are unchanged;
data-quality acceptance does not imply inclusion in any training dataset.
