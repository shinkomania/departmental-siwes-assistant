# E2.5 CHECKPOINT

## Academic Directory Publication & Provenance

### Git
- Branch: phase4-programme-siwes-config
- Commit: 514b7e7
- Commit message: Harden academic directory publication against duplicate source rows
- Worktree: clean

### Database
- Migration head: 8ff375472875

### Verified authoritative sources
- Nigerian Universities Commission (NUC)
- National Board for Technical Education (NBTE)

### Verified live directory sizes
- NUC: 328 records
- NBTE: 208 records

### Publication safety
- Existing source identity handling: verified
- New institution publication: verified
- Exact canonical institution matching: verified
- Duplicate authoritative source rows: verified
- Duplicate source rows are safely skipped
- Source identity uniqueness is preserved
- Source evidence/provenance creation is covered
- Dry-run safety: verified
- Rollback integrity: verified
- Full NUC publication trial: verified
- Full NBTE publication trial: verified

### NBTE duplicate source rows
The live NBTE directory contains two duplicate normalized-name groups:
- First City Polytechnic, Abeokuta, Ogun State
- Raindrops Institute of Management and Technology, Amannachi, Orsu LGA, Imo State

These are handled without weakening database uniqueness constraints.

### Regression
- Full test suite: 292 tests passed

### Status
E2.5 academic directory publication/provenance checkpoint complete.
No further E2.5 code changes should be made without a new controlled step.
