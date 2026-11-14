# Sprint 5 database documentation verification

Documentation snapshot: **November 13, 2026, America/Los_Angeles**. This task used read-only PostgreSQL catalogs, a schema-only export, Git reads and existing reports. It did not execute migrations, seed data, HTTP mutation requests, tests with database writes, or service restarts. Previously modified application files and Git state were preserved; only the seven requested documentation artifacts were created under `backend/docs/database/`.

## Sources and provenance

| Evidence | What it establishes | Limit |
|---|---|---|
| `git show 1202e94:backend/app/database/sports_prediction_schema.sql` | Earliest tracked Sprint 1 SQL: 13 tables, no password-hash column | Source introduction is not a database migration execution timestamp. |
| `git diff 1202e94 5a9d0a0 -- backend/app/database/sports_prediction_schema.sql` | October 1 source addition of `users.password_hash VARCHAR(255) NOT NULL` | Source file changed before that column was actually applied locally. |
| `git log --diff-filter=A -- backend/app/database/auth_tables.py`, commit `2a4223e` | Four auth table definitions originated in Sprint 4, November 5 | Local application date comes from setup evidence, not Git. |
| `../sprint5_virtual_betting_schema.sql`, `app/database/auth_tables.py`, `app/database/betting_tables.py` | Nine-table additive definition set; four reused auth plus five new betting tables | Preview omits the separately approved users-column ALTER. Sprint 5 files are supplied on the feature branch. |
| `sprint5_actual_schema.sql` and read-only PostgreSQL catalogs | Physical definitions currently in local development database | Schema metadata does not establish that every feature uses every table. |
| `../sprint5_local_setup_results.md` | Prior backup, application approvals, migrations, live HTTP workflow and restart evidence | Historical execution report, not re-executed during documentation. |
| `build/sprint5-complete-tests.xml`, `build/sprint5-http-tests.xml` | Machine-readable prior test outcomes; totals and named concurrency cases independently inspected in this documentation task | Ignored build artifacts may be absent in another clone; preserve them with submission evidence if required. |

Paths beginning `build/` or `app/` in this document are relative to repository root or `backend/` respectively. No test user records, stored password hashes, session values, credentials or connection strings are reproduced.

## Export procedure and scope

Target identity was verified using a read-only transaction: database **`sports_betting`**, server loopback (`::1`), port **5432**. The separate test database is not the target of this export.

The schema export used the equivalent of:

```text
pg_dump --schema-only --no-owner --no-privileges --no-comments --no-security-labels
```

Connection parameters came from existing local settings; credentials were supplied privately in the child environment and are absent from the artifacts. The dump process used `PGOPTIONS=-c default_transaction_read_only=on`. Ownership/ACL/comment/security-label metadata was intentionally omitted for a portable, credential-free design reference. Generated `\restrict`/`\unrestrict` guard-key lines, which are pg_dump control markers rather than application records, were omitted to keep the reference free of token-like values. No DDL was executed against a database to validate this documentation.

The export includes table definitions, column nullability/defaults, keys, CHECKs, indexes, owned sequences, extension declarations and schema DDL. It contains no COPY/INSERT application data, role definitions, ownership assignments or sequence-counter `setval` calls. Sequence start/increment/min/max/cache/cycle are definitions, not current application data.

No application views, materialized views, user-schema functions/procedures or triggers were present to export. PostgreSQL system functions are not application objects. No identity columns were found; serial columns use owned sequences.

## Current physical schema results

| Item | Verified count |
|---|---:|
| User tables | 22 |
| Columns | 138 |
| Primary keys | 22 |
| Foreign keys | 26 |
| Unique constraints | 12 |
| CHECK constraints | 17 |
| Total table constraints | 77 |
| Indexes, including primary/unique backing indexes | 44 |
| Sequences | 17 |
| Views / materialized views / user-schema functions / application triggers | 0 / 0 / 0 / 0 |

All catalogued constraints have `convalidated=true`. All catalogued indexes have `indisvalid=true` and `indisready=true`. NOT NULL is recorded per column and is not included in the 77 table-constraint count. These are catalog validation checks, not a new data consistency or performance test.

## Three-way schema comparison

- Historical baseline: exactly 13 tables. Current source at `app/database/sports_prediction_schema.sql` differs from its historical revision by the later password-hash addition.
- Nine-table preview: exactly four auth and five virtual-betting tables. Every expected table exists in the actual development schema. Its column types/nullability/defaults, PK/FK/unique structures and CHECK expressions were compared to the catalog.
- Compared 137 source-defined columns/defaults across baseline plus additions. The live schema has those 137 plus the separately approved `users.password_hash`. Its actual type is VARCHAR(255), NOT NULL, with no default.
- The comparison normalized PostgreSQL aliases, sequence-backed serial defaults, default-expression casts and CHECK deparsing. All 17 checks matched after those representational normalizations. Original named checks and all eight explicit Sprint 1 indexes are present. Exact physical definitions are recorded in the inventory and export.
- No missing expected table, column, PK, FK, unique constraint, CHECK or explicit index was identified. No unexpected application table, view, function or trigger was found.
- Physical column order differs for `users.password_hash`: live last column versus source insertion before `is_active`. No claim of byte-identical SQL dumps is made.

The three files are intentionally **not identical**: one is a historical baseline, one is a partial addition preview, and one is a full PostgreSQL-generated snapshot. The preview is not a complete migration record because it excludes the password-hash ALTER.

## ER and flow quality checks

`sprint5_database_erd.mmd` includes all **22 verified entities, 138 columns and 26 FK edges**. An automated metadata comparison checked that every entity exists, every column is present, every FK targets an actual referenced table/column, and graph edges exactly match the physical FK set. Parent optionality comes from child-column nullability; child maximum-one cardinality comes from unique/primary-key coverage. Composite uniqueness is described in the inventory; it is not falsely shown as separate individual unique columns.

The two intentionally independent challenge/throttle entities are included without invented user FKs. No FK is invented for external entity IDs or ledger reference strings. ER completeness concerns the physical schema, not hypothetical future integration relationships.

`sprint5_database_flows.mmd` is one validly structured `flowchart TD` document containing six labeled subgraphs: registration, login/session persistence, match selection, bet placement/deduction, won/lost/void settlement, and persistence verification. Flows were checked against current route/service/CLI source. They describe what application code does; this documentation task did not execute the depicted writes. Diagram source was structurally checked; rendered Mermaid visual layout was not verified in this task. The full 22-table ER may need landscape layout or multiple presentation panels for Word/PDF publication.

## Prior implementation and migration results

The prior local setup report records a successful backup, followed by creation of nine missing tables and their additive objects. It then records an approved correction of the missing `users.password_hash` column after verifying an empty users table. Original reference records were preserved; the implementation created only authorized synthetic fixtures and test workflow records. These are prior results, not new migration operations in this task.

Virtual points have no cash value. Synthetic fixture/odds provenance comes from `app/database/virtual_demo_fixtures.py` and the setup report. The physical match table has no dedicated demo-provenance field. The inventory and evolution document distinguish SQL-enforced constraints from application-enforced eligibility, cross-table consistency, transaction, retry and settlement rules.

## Prior automated and HTTP evidence

The JUnit files were parsed during documentation and confirm:

- Full backend suite: **510 passed, 0 failed, 62 skipped**.
- Separate HTTP-mode invocation: **2 passed, 0 failed**; the prior console/report records 96 deselections.
- Both named PostgreSQL concurrency cases (`test_postgres_concurrent_requests[postgres-True]` and `[postgres-False]`) are passing, not skipped. They cover concurrent duplicate retries and competing wallet stakes.

Full-suite skip attribution from JUnit: 52 Sprint 4 PostgreSQL cases need their separately guarded database/configuration; four historical-import cases need another authorized disposable database; one PostgreSQL security module was skipped at collection; two SQLite concurrency variants require PostgreSQL row locks; one fault-injection trigger is SQLite-only; two HTTP-mode variants were run successfully in the separate invocation. Thus the 62 skips are reported, not counted as passes.

The prior live HTTP report records starting points, stake deduction, winning settlement, repeated settlement without another payout and persistence of user/session/wallet/bet after stopping and restarting Uvicorn. This documentation cites that prior verification without exporting the report's user-identifying fields or copying authentication material. It does not claim every loss/void scenario was exercised live against development; automated isolated tests cover those cases.

## Remaining gaps and limitations

- Git cannot prove the original installation time of each local schema object. There is no versioned migration ledger documenting all local execution events.
- Four auth table definitions predate Sprint 5 even though their local creation occurred during Sprint 5 setup; five betting definitions are new. That distinction must survive final report editing.
- The standalone nine-table preview and preparation-era handoff text are incomplete/current-status-limited sources. Prefer the actual export for physical design and the local setup report for completed execution evidence.
- Existing prediction blockers remain as previously reported: missing trained artifacts can produce an unhandled 500 from `/predictions`, and match predictions require completed history. No ML behavior was retested or changed here.
- Frontend login remains a prototype according to the prior report. A complete database ER does not imply completed frontend integration.
- Cross-table bet/outcome consistency, league-specific outcome eligibility, ledger reconciliation, accepted-odds validation and settlement transitions are partly application-enforced, not all independently constrained by PostgreSQL.
- Diagram rendering and a restored-schema execution drill were not performed. No new tests or data mutations were run for documentation.

## Artifact integrity

- Historical SQL SHA-256: `f1faa702a8ace13a69398a7d4344a4f67411fca2f05fd99a430a06aec715f91b` (byte-for-byte match to Git revision `1202e94`).
- Actual schema-only SQL SHA-256: `c7fa15a682fb1ecd70f3ded35d57492b545c9efdb46d67e34ce1d76c31770436` (after documented removal of pg_dump guard-key lines and normalization of the final newline).

The seven deliverables form a read-only documentation package. No application code, database objects/records, Git branch, commits, running services or local configuration were changed.
