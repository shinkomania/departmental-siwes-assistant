# DSA Current Development Checkpoint

## Current Branch

`phase4-programme-siwes-config`

## Current Implementation Baseline

Latest implementation commit:

`796c7de Refresh platform administration attention dashboard`

Recent completed milestones:

- `8654703` - Directory Request Eligibility + Profile Cleanup
- `06bd46f` - Reviewer Case Workspace
- `5714446` - Reusable User Notification System
- `1361f41` - Directory Workflow Notification Integrations
- `796c7de` - Platform Administration Attention Dashboard

The implementation working tree was clean immediately after commit `796c7de`.

## Verification Baseline

At completion of Milestone D:

- 252 full-suite tests passed in 82.292 seconds;
- focused Platform Administration dashboard tests passed;
- the previously existing admin authentication/dashboard regression test passed after updating its stale heading expectation;
- `git diff --check` reported no whitespace errors;
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

`796c7de Refresh platform administration attention dashboard`

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

## Immediate Next Step - Controlled Directory Publication

The next major development target is the controlled authoritative academic-directory workflow.

The goal is to move from an approved request to a deliberate, auditable authoritative directory action without weakening the review/publication boundary.

Before implementation, inspect the existing:

- `Institution`;
- `AcademicUnit`;
- `Department`;
- `Programme`;
- verification/status fields;
- current Platform Administrator authorization;
- approved DirectoryRequest data contract.

Design requirements:

- no automatic publication on request approval;
- explicit Platform Administrator publication action;
- validate hierarchy before creation;
- prevent duplicate authoritative records;
- preserve request history;
- record who performed the publication action;
- make publication auditable;
- expose only valid active/verified authoritative records to student selection flows;
- preserve programme-level SIWES configuration and eligibility rules;
- design for later institution-managed directory maintenance without granting it prematurely.

Do not create fake navigation routes for directory areas that do not yet exist.

After Controlled Directory Publication:

1. Staff Access Requests and scoped staff workspaces.
2. Broader account/profile/onboarding and workspace switching.
3. Evidence/attachment architecture where it best fits the workflow.

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
