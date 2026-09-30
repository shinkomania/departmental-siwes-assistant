# DSA Current Development Checkpoint

## Current Branch

`phase4-programme-siwes-config`

## Current Implementation Baseline

Latest implementation commit:

`1361f41 Integrate directory workflow notifications`

Recent completed milestones:

- `8654703` - Directory Request Eligibility + Profile Cleanup
- `06bd46f` - Reviewer Case Workspace
- `5714446` - Reusable User Notification System
- `1361f41` - Directory Workflow Notification Integrations

The repository working tree was clean immediately after commit `1361f41`.

## Verification Baseline

At completion of Milestone C4:

- 5 focused C4 workflow-notification tests passed;
- 44 directory-request regression tests passed;
- 2 clarification regression tests passed;
- 20 notification regression tests passed;
- 251 full-suite tests passed in 80.378 seconds;
- Python compilation checks passed;
- `git diff --check` reported no whitespace errors;
- only the known Windows LF/CRLF conversion warning remained;
- real directory-review notification flow passed on desktop;
- real directory-review notification flow passed at approximately 390 x 844 mobile size;
- notification bell unread count, notification centre, safe preview text and protected destination navigation were manually validated.

Known non-failing technical debt:

- SQLAlchemy legacy `Query.get()` warnings remain elsewhere in the application.
- Windows Git may report LF/CRLF working-tree conversion warnings.

## Completed Milestone C - Reusable DSA Notifications

DSA has a reusable user-level notification subsystem.

Notifications belong to `User`, not `StudentProfile`.

Core implementation:

- `models/notification.py`
- migration `8f5d74b88835_add_reusable_user_notifications.py`
- `services/notification_service.py`
- `routes/notifications.py`
- `templates/notifications/index.html`
- global signed-in notification bell and unread-count badge.

Notification data supports:

- recipient user;
- category;
- notification type;
- title;
- message;
- priority;
- controlled internal action URL;
- generic source type and source ID;
- read timestamp;
- creation timestamp.

Read state is derived from `read_at`.

### Notification Security Contract

Notification ownership is a hard authorization boundary.

User A must never be able to view, count, mark as read, open, or bulk-modify User B's notifications.

This is enforced in service and HTTP-route layers.

Platform Administrator authority does not automatically grant access to another user's private notification inbox.

Inactive/suspended accounts cannot use stale sessions to access notification routes.

Notification action URLs provide navigation only. Destination routes independently enforce ownership, permission and scope.

## Completed Milestone C4 - Directory Workflow Notifications

Real directory-review events now use the reusable notification system.

Implemented events:

1. Reviewer requests clarification -> requester receives notification.
2. Requester submits clarification -> assigned reviewer receives notification.
3. Reviewer approves request -> requester receives notification.
4. Reviewer rejects request -> requester receives notification.

Current notification types:

- `directory_clarification_requested`
- `directory_clarification_response_received`
- `directory_request_approved`
- `directory_request_rejected`

Directory workflow notifications use:

- category `Directory & Reviews`;
- recipient-specific notification rows;
- `DirectoryRequest` source metadata;
- permission-safe internal action destinations;
- the same database transaction as the associated workflow change where implemented.

Sensitive reviewer notes, clarification text, evidence references and similar private workflow content are not copied into notification preview messages.

The requester notification links to:

`/academic/directory-requests/<request_id>`

The reviewer notification links to:

`/admin/directory-requests/<request_id>`

Those destination routes independently enforce requester ownership or Platform Administrator authorization.

### Directory Review Invariant

DirectoryRequest review state remains separate from authoritative academic directory publication.

Approving a DirectoryRequest must not automatically create or verify an Institution, AcademicUnit, Department or Programme.

C4 includes regression coverage protecting this boundary.

Clarification ownership remains:

- Platform Admin claims Submitted request;
- request becomes Under Review;
- claiming reviewer may request clarification;
- request becomes More Info Required;
- requester responds;
- request returns to Under Review;
- original reviewer remains assigned.

## Evidence / Attachment Future Requirement

Directory-request evidence is currently text/reference based.

Future evidence handling should support reusable evidence items such as:

- official/reference URL;
- document or image attachment;
- supporting note.

Evidence must remain supporting material only and must never automatically verify or publish an academic record.

Future file handling should include server-side file validation, safe generated filenames, size/type restrictions, protected access where necessary and storage abstraction suitable for later object/cloud storage.

Do not expand this into C4 retroactively.

## Immediate Next Step - Milestone D

Begin the Platform Administration refresh.

The Platform Administration dashboard should answer:

**What needs my attention? What is happening on DSA? Where do I need to go?**

Planned direction:

- Admin Attention Centre;
- concise overview rather than organization-review dominance;
- dedicated Platform Administration navigation;
- clearer separation of reviews, academic directory, organizations, users/access and SIWES content;
- recent/urgent items on Overview with links to dedicated queues;
- preserve permission-based Platform Administration authorization;
- maintain modern, sharp, responsive and professional DSA design.

Planned Platform Administration navigation direction:

**Overview | Reviews | Academic Directory | Organizations | Users & Access | SIWES Content**

Academic Directory direction:

**Requests | Institutions | Academic Units | Departments | Programmes**

Request views should eventually support useful states such as:

- Submitted
- Assigned to Me
- Awaiting Student
- Response Received
- Approved
- Rejected
- Withdrawn

Do not mix Platform Administration with Institution or Department Coordinator workspaces.

After Milestone D:

1. Controlled Directory Publication.
2. Staff Access Requests and scoped workspaces.
3. Broader account/profile/onboarding/workspace-switching development.

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
