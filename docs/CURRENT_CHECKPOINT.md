# DSA Current Development Checkpoint

## Current Branch

`phase4-programme-siwes-config`

## Current Implementation Baseline

Latest implementation commit:

`eadb609 Add canonical academic directory identity`

Recent completed milestones:

- `8654703` - Directory Request Eligibility + Profile Cleanup
- `06bd46f` - Reviewer Case Workspace
- `5714446` - Reusable User Notification System
- `1361f41` - Directory Workflow Notification Integrations
- `796c7de` - Platform Administration Attention Dashboard

The implementation working tree was clean immediately after commit `796c7de`.

## Verification Baseline

Current verified implementation baseline:

- implementation commit: `eadb609 Add canonical academic directory identity`;
- migration revision: `5f733fe82e7c` (`head`);
- real development database successfully migrated from E1.1 `0f5b0cfdfb95` to E1.2 `5f733fe82e7c`;
- 267 full-suite tests passed;
- 11 focused canonical academic-directory identity tests passed;
- migration round-trip E1.1 -> E1.2 -> E1.1 -> E1.2 passed on a disposable database;
- Institution, AcademicUnit, Department and Programme canonical-collision cases were each rejected before E1.2 DDL mutation;
- academic-directory records were preserved during real migration;
- canonical identity fields were backfilled correctly;
- SQLite `integrity_check` returned `ok`;
- SQLite foreign-key verification passed;
- ORM models and physical E1.2 schema were verified synchronized;
- `git diff --check` reported no whitespace errors before commit;
- repository was clean after deployment;
- verified physical E1.1 recovery backup is being retained.

Historical Milestone D verification included:

- 252 full-suite tests passed in 82.292 seconds;
- focused Platform Administration dashboard tests passed;
- the previously existing admin authentication/dashboard regression test passed after updating its stale heading expectation;
- desktop Platform Administration UI was manually validated;
- responsive UI at approximately 390 x 844 was manually validated;
- Attention Centre cards, counts, action hierarchy and responsive stacking were manually validated.

Known non-failing technical debt:

- SQLAlchemy legacy `Query.get()` warnings remain elsewhere in the application and should be migrated deliberately to SQLAlchemy 2.x-style session access later.
- Windows Git may report LF/CRLF working-tree conversion warnings.

## Completed Milestone C - Reusable DSA Notifications

DSA has a reusable user-level notification subsystem.

Notifications belong to `User`, not `StudentProfile`.

Core behavior includes:

- recipient-scoped notification ownership;
- category, type, title, message and priority;
- controlled internal action URLs;
- generic source metadata;
- read state derived from `read_at`;
- notification bell and unread count;
- notification centre with individual and bulk read actions.

### Notification Security Contract

User A must never be able to view, count, mark as read, open or bulk-modify User B's notifications.

Platform Administrator authority does not automatically grant access to another user's private notification inbox.

Notification action URLs provide navigation only. Destination routes independently enforce ownership, permission and scope.

## Completed Milestone C4 - Directory Workflow Notifications

Real directory-review events use the reusable notification system.

Implemented events:

1. Reviewer requests clarification -> requester.
2. Requester submits clarification -> assigned reviewer.
3. Reviewer approves request -> requester.
4. Reviewer rejects request -> requester.

Sensitive reviewer notes, clarification text and evidence references are not copied into notification preview messages.

Clarification ownership remains:

- Platform Admin claims Submitted request;
- request becomes Under Review;
- claiming reviewer may request clarification;
- request becomes More Info Required;
- requester responds;
- request returns to Under Review;
- original reviewer remains assigned.

## Completed Milestone D - Platform Administration Refresh

Implementation commit:

`eadb609 Add canonical academic directory identity`

The Platform Administration overview now answers:

**What needs my attention? What is happening on DSA? Where do I need to go?**

### Attention Centre

The dashboard now surfaces:

- pending organization reviews;
- new Submitted academic-directory requests;
- the current Platform Administrator's active directory reviews;
- cases assigned to the current Platform Administrator that are awaiting requester clarification;
- clarification responses that are ready for the assigned reviewer.

Assignment-sensitive directory counts are scoped to the current Platform Administrator.

`Response Received` is a derived operational signal, not a persisted DirectoryRequest status.

It is derived when:

- the request is `Under Review`;
- it remains assigned to the current reviewer; and
- the latest clarification message was authored by the requester.

The actionable total deliberately does not add `Response Received` separately because it is a subset of active reviews. This prevents double counting.

The current latest-response derivation uses the latest `DirectoryRequestMessage` ID as the append-only ordering signal. If imported or externally sequenced events are introduced later, move to an explicit event sequence/timestamp contract.

### Platform Administration UI

The dashboard heading is now:

`Platform Administration`

The former organization-heavy overview has been rebalanced around operational attention while preserving:

- platform metrics;
- recent organization review preview;
- recent users;
- quick administration actions;
- evidence/governance guidance.

The Attention Centre has dedicated responsive behavior for desktop, tablet and mobile layouts and respects reduced-motion preferences.

Do not mix Platform Administration with future Institution or Department Coordinator workspaces.

### Scalability Direction

The current dashboard uses several focused count queries plus a latest-message subquery. This is appropriate for the present scale.

As attention signals and platform volume grow, consider moving dashboard aggregation into a dedicated service/read model with appropriate database indexes rather than expanding route-level query logic indefinitely.

## Directory Review / Publication Invariant

DirectoryRequest review state remains separate from authoritative academic directory creation, verification and publication.

**Approving a DirectoryRequest must not automatically create or verify an Institution, AcademicUnit, Department or Programme.**

Approved requests are review decisions only.

Authoritative academic records require a separate deliberate publication workflow.

## Completed E1.2 - Canonical Academic Directory Identity

Implementation commit:

`eadb609 Add canonical academic directory identity`

Migration:

`5f733fe82e7c Add canonical academic directory identity`

E1.2 establishes database-backed canonical identity for the authoritative academic hierarchy.

Canonical identity contract:

- Institution identity: `normalized_name`;
- AcademicUnit identity: `(institution_id, normalized_name)`;
- Department identity: `(academic_unit_id, normalized_name)`;
- Programme identity: `(department_id, normalized_name, normalized_award)`.

Normalization is deliberately conservative. It provides stable identity matching without attempting unsafe semantic equivalence between genuinely different academic names or awards.

The canonical identity keys are derived automatically by the academic models and resynchronize when their display identity values change.

Database uniqueness constraints enforce the same identity contract used by the application.

### Legacy Migration Safety

E1.2 performs legacy canonical-collision validation before schema-changing DDL.

The migration deliberately refuses to proceed when legacy records would collapse into the same canonical identity.

Failure-path testing verified this independently for:

- Institution;
- AcademicUnit;
- Department;
- Programme.

For every collision class:

- the migration failed with a controlled diagnostic;
- the Alembic revision remained at E1.1;
- no E1.2 canonical columns were introduced;
- the failure therefore occurred before E1.2 DDL mutation.

This pre-DDL validation is particularly important for SQLite because migration DDL must not be assumed to provide fully transactional rollback behavior.

### Real Database Deployment

The development database was backed up and the backup SHA256 was verified against the source before deployment.

The real development database was then migrated successfully:

`0f5b0cfdfb95 -> 5f733fe82e7c`

Post-deployment verification confirmed:

- all existing academic-directory records were preserved;
- all canonical identity fields were backfilled correctly;
- SQLite integrity passed;
- foreign-key verification passed;
- ORM/schema synchronization passed;
- repository remained clean.

The verified E1.1 pre-migration backup must be retained for now.

### Architectural Significance

Canonical identity is infrastructure for the trusted national academic directory rather than a user-facing search heuristic.

It provides a stable basis for later:

- controlled source imports;
- deterministic matching of source candidates against authoritative records;
- duplicate prevention;
- aliases and abbreviations without creating duplicate canonical entities;
- DirectoryRequest publication;
- academic-directory enrichment;
- stronger discovery and missing-data UX.

Canonical identity does not itself establish recognition, verification, publication authority or SIWES eligibility. Those remain separate trust claims governed by source/provenance and publication workflows.

## Immediate Next Step - Milestone E: Trusted Academic Directory Foundation

The next major development target is no longer publication in isolation. DSA should first establish a trusted, source-backed national academic-directory foundation so that student requests become an exception and correction mechanism rather than the primary way the platform discovers Nigerian institutions.

### Core Directory Strategy

DSA should progressively seed and maintain its authoritative directory from recognized official sources.

Current source-authority direction:

- NUC for universities and university/programme recognition;
- NBTE for polytechnics and relevant TVET institutions/programmes;
- NCCE for Colleges of Education;
- JAMB IBASS as an important institution/programme discovery and cross-check source;
- official institution sources for internal Faculty/College/School, Department and programme structure;
- institution SIWES offices, approved institutional documentation and relevant ITF evidence for SIWES-specific configuration.

Official-source data must not be copied blindly. Recognition of an institution or programme does not prove every contact field, internal academic structure or SIWES rule.

### Separate Verification Claims

DSA must keep these concepts distinct:

1. Institution recognition/verification.
2. Programme recognition/availability.
3. Internal academic-structure verification.
4. Programme SIWES eligibility/configuration.

A programme appearing in NUC, NBTE, NCCE, JAMB or another recognition source must never automatically make that programme SIWES-enabled.

### Source Provenance

Authoritative directory data should be traceable to its supporting source.

Design for reusable source/provenance records capable of recording:

- source authority;
- source/reference URL or identifier;
- entity type and entity;
- verification purpose;
- checked/reviewed timestamp;
- responsible reviewer or import process;
- source version/snapshot/hash where practical;
- notes.

Do not scatter unrelated publication metadata across every academic model if a reusable provenance/audit architecture provides a cleaner solution.

### Controlled Import Direction

Do not build production directory maintenance around fragile live scraping or automatic source overwrites.

Preferred flow:

Official Source -> Import Candidate -> Normalize -> Match/Compare -> Review -> Publish

Source changes should be reviewable before changing authoritative DSA records.

Future source synchronization may identify:

- new records;
- matched/unchanged records;
- changed records;
- possible duplicates;
- records requiring human review.

### Missing Institution / Programme UX

"Can't find your institution?" and "Can't find your programme?" should become exception workflows.

Before offering a request:

- provide strong search;
- support canonical names and aliases/abbreviations;
- later support safe fuzzy matching;
- search by relevant location/context where useful.

Institution aliases should eventually support official abbreviations, former names, common abbreviations and alternative spellings while preserving one canonical Institution record.

If a genuinely missing institution or programme remains, the user may submit a DirectoryRequest for review.

A DirectoryRequest must never directly become authoritative directory data.

### Milestone E Progression

#### E1 - Source and Provenance Architecture

Inspect and design the reusable source/provenance and authoritative-directory data contract.

#### E2 - Controlled National Institution Seed / Import

Build a reviewed import path for establishing a strong Nigerian institution baseline from recognized official sources without silent production overwrites.

#### E3 - Controlled DirectoryRequest Publication

Build the deliberate Platform Administrator workflow that can turn an approved request into authoritative directory data through the same trusted publication principles.

Requirements remain:

- no automatic publication on request approval;
- explicit authorized publication action;
- hierarchy validation;
- duplicate prevention;
- preserved request history;
- publication provenance and actor accountability;
- atomic authoritative changes where practical.

#### E4 - Programme and Academic-Hierarchy Enrichment

Progressively enrich Institution -> AcademicUnit -> Department -> Programme data from reliable sources.

Do not infer an institution's internal hierarchy merely from a programme name when an authoritative institutional structure has not been established.

#### E5 - Directory Discovery and Missing-Data UX

Improve canonical search, aliases, safe fuzzy discovery and the "Can't find..." workflows so requests handle genuine omissions/corrections rather than ordinary search failures.

### Lifecycle Principle

Verified, active, suspended and inactive are not interchangeable concepts.

Historical authoritative records should generally be preserved rather than deleted merely because an institution or programme later becomes inactive or changes status.

### Scalability Direction

As DSA matures, Platform Administration may gain an Academic Directory workspace such as:

Overview | Institutions | Academic Units | Departments | Programmes | Requests | Source Sync

Do not create navigation or routes for these areas until their real workflows exist.

### After Milestone E

Current broader roadmap remains:

1. Staff Access Requests and scoped staff workspaces.
2. Broader account/profile/onboarding and workspace switching.
3. Evidence/attachment architecture where it best fits the workflow.

## Live SIWES / Trusted Data Future Direction

Milestone E source/provenance architecture should be reusable enough to support
trusted academic-directory data and later organization/placement intelligence
without treating their verification rules as identical.

Important future direction:

- an Organization is a relatively persistent directory entity;
- a SIWES opportunity/intake is time-sensitive and should eventually be modeled
  separately rather than overwriting organization history;
- live opportunity information should support source freshness, first/last seen
  timestamps, deadlines/expiry where known and lifecycle states such as Active,
  Stale, Closed/Expired and Archived;
- external source synchronization should use controlled adapters/import jobs
  rather than fragile logic inside normal web requests;
- synchronization must record source health/freshness so DSA never presents stale
  data as freshly confirmed;
- trustworthy routine updates should be automated where practical, while
  suspicious, conflicting, unmatched or low-confidence changes should be routed
  to human review;
- official-source evidence, institution/coordinator evidence,
  organization-confirmed information and student/community signals must retain
  their different meanings and provenance;
- student reports such as "still accepting", "applications closed" and
  "I was accepted here" should become structured signals that may corroborate
  placement intelligence but must not automatically become authoritative facts;
- future official DSA communities/channels may be linked to canonical
  institutions, programmes, organizations, SIWES sessions or opportunities;
- community discussion must remain separate from structured signals and from
  Official Notices;
- programme-aware opportunity matching should eventually connect trusted/live
  placement evidence with the student's academic context;
- DSA should remain a discovery, matching, coordination and workflow layer and
  should prefer official integrations where available rather than impersonating
  users or automating external submissions without authorization.

Standing principle:

**Automate routine evidence-backed updates where practical; use human review for
exceptions; never automate trust beyond what the evidence actually proves.**

Build now:
- reusable source/provenance foundations needed by Milestone E.

Design now, implement later:
- source synchronization/import runs;
- source-health monitoring;
- SIWESOpportunity and opportunity history;
- freshness/expiry policies;
- programme-aware placement matching;
- structured student/coordinator/employer signals.

Defer safely:
- real-time chat/community infrastructure;
- WebSockets/push infrastructure;
- advanced community moderation;
- direct external-system submission/integration unless an authorized integration
  mechanism exists.

## Evidence / Attachment Future Requirement

Directory-request evidence is currently text/reference based.

Future evidence handling should support reusable evidence items such as:

- official/reference URL;
- document or image attachment;
- supporting note.

Evidence must remain supporting material only and must never automatically verify or publish an academic record.

Future file handling should include server-side validation, safe generated filenames, size/type restrictions, protected access where necessary and storage abstraction suitable for later object/cloud storage.

## Standing Identity / Authority Direction

DSA should evolve toward:

**One DSA Account. Multiple approved profiles/roles. One controlled authority structure.**

`User` represents identity.

`StudentProfile` represents student context.

Future staff-access requests represent requests for authority.

`UserRoleAssignment` represents approved scoped authority.

A user may legitimately hold both student context and approved staff authority without creating multiple accounts.

Platform Administrator authority must remain permission-based rather than a generic `is_admin` flag.

The future Primary Platform Administrator / Platform Owner must be modeled securely and must not depend on a hard-coded person's name.

## Standing Product / Engineering Principles

For every feature, proactively consider:

- security and least privilege;
- privacy;
- audit trails;
- database integrity;
- scalability;
- reusable architecture;
- mobile responsiveness;
- accessibility;
- file/evidence safety;
- concurrency;
- useful empty/error/success states;
- performance;
- future multi-institution expansion.

Distinguish between:

- build now;
- design for now, implement later;
- defer safely.

Avoid overengineering that delays shipping.

## Development Workflow

Use:

**inspect -> one controlled change -> targeted test -> broader/full test -> desktop UI test -> mobile/responsive UI test -> commit -> checkpoint at meaningful milestones.**

Prefer direct Windows venv execution:

`.\venv\Scripts\python.exe`

Prefer guarded PowerShell changes when practical.

Do not perform large uncontrolled rewrites.

Keep inspection output small because large PowerShell output is easily truncated.

The repository and current tests override stale documentation.
