# Sprint 3 Data Validation Checklist

## Purpose

Plan the data-engineering review of NBA, NFL, and UEFA match records before
using them for match prediction.

**Status: Planning checklist only. Validation tests have not yet been executed
for this checklist.**

## Checklist

- [ ] Confirm each match has a non-empty, valid match ID for its data source.
- [ ] Confirm home and away team identifiers are present, resolve to known teams,
      and identify different teams.
- [ ] Confirm match dates use a consistent ISO 8601 format (`YYYY-MM-DD` for
      dates, with an explicit UTC offset or `Z` for timestamps).
- [ ] Flag missing or incomplete required fields; distinguish expected missing
      scores for scheduled matches from missing results for completed matches.
- [ ] Check for duplicate match records using the data source and match ID.

## Next Steps

Review sample records from each sport, carry out the planned validation checks,
and record findings and any required data corrections before marking items complete.
