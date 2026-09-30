# DSA Current Development Checkpoint

## Current Branch

`phase4-programme-siwes-config`

## Current Implementation Baseline

Latest implementation commit:

`5714446 Add reusable user notification system`

Previous completed milestones:

- `8654703` - Directory Request Eligibility + Profile Cleanup
- `06bd46f` - Reviewer Case Workspace
- `5714446` - Reusable User Notification System

The repository working tree was clean immediately after commit `5714446`.

## Verification Baseline

At completion of the reusable notification foundation:

- 246 full-suite tests passed;
- notification model/service tests passed;
- 7 focused notification HTTP/security tests passed;
- `py_compile` passed for notification-related Python modules;
- `git diff --check` reported no whitespace errors;
- desktop notification UI passed;
- 390 x 844 mobile notification UI passed;
- populated notification state passed;
- read-state transition and bell-count update passed.

Known non-failing technical debt:

- SQLAlchemy legacy `Query.get()` warnings remain elsewhere in the application.
- Windows Git may report LF/CRLF working-tree conversion warnings.

## Completed Milestone C - Reusable DSA Notifications

DSA now has a reusable user-level notification subsystem.

Notifications belong to `User`, not `StudentProfile`.

Implemented model:

`models/notification.py`

Implemented migration:

`8f5d74b88835_add_reusable_user_notifications.py`

Implemented reusable service:

`services/notification_service.py`

Implemented global routes:

`routes/notifications.py`

Implemented notification centre:

`templates/notifications/index.html`

The signed-in global header now contains a notification bell with an
unread-count badge.

### Notification Data Contract

The current notification model supports:

- recipient user;
- category;
- notification type;
- title;
- message;
- priority;
- internal action URL;
- generic source type and source ID;
- read timestamp;
- creation timestamp.

Read state is derived from `read_at`. There is no duplicate persisted
`is_read` boolean.

Current categories include:

- Directory & Reviews
- Placements
- SIWES
- Official Notices
- Access & Security
- Organizations
- System

Current priorities include:

- Normal
- Important
- Urgent

### Security Contract

Notification ownership is a hard authorization boundary.

User A must never be able to view, count, mark as read, open, or
bulk-modify User B's notifications.

This is enforced by the service and HTTP routes rather than relying only
on the interface.

Foreign notification IDs return no usable private inbox access.

Platform Administrator authority does not automatically grant access to
another user's private notification inbox.

Inactive/suspended accounts cannot use stale sessions to access the
notification centre.

Notification action URLs provide navigation only. Destination routes
must independently enforce ownership, permission and scope.

Only controlled internal DSA paths are currently accepted as
notification action URLs.

## Notification UI

The notification centre currently provides:

- unread and total counts;
- category labels;
- Important and Urgent priority cues;
- visible unread state;
- timestamps;
- Mark as read;
- Mark all as read;
- contextual View update actions;
- polished empty state;
- responsive mobile behavior.

A JavaScript-heavy notification dropdown is intentionally deferred.

Pagination becomes necessary before production-scale notification
volume.

Future preferences, category muting, email/push/SMS delivery, batching,
digests, WebSockets and notification analytics remain deferred.

## Directory Review Invariants

DirectoryRequest review state remains separate from authoritative
academic directory publication.

Approving a DirectoryRequest must not automatically create or verify an
Institution, AcademicUnit, Department or Programme.

Clarification ownership remains:

- Platform Admin claims Submitted request;
- request becomes Under Review;
- claiming reviewer may request clarification;
- request becomes More Info Required;
- requester responds;
- request returns to Under Review;
- original reviewer remains assigned.

The next notification integration must preserve these rules.

## Immediate Next Step - Milestone C4

Connect real directory-review workflow events to the reusable
notification system.

Initial events:

1. Reviewer requests clarification -> notify requester.
2. Requester submits clarification response -> notify assigned reviewer.
3. Reviewer approves request -> notify requester.
4. Reviewer rejects request -> notify requester.

Notifications should link to the appropriate permission-safe DSA
destination.

Where practical, the domain change and notification should participate
in the same database transaction so one does not succeed while the
other fails.

Do not put directory-specific business logic inside the generic
notification service.

Do not change approval into authoritative publication.

After C4, proceed to:

1. Platform Administration dashboard/navigation refresh.
2. Controlled Directory Publication.
3. Staff Access Requests and scoped workspaces.
4. Broader account/profile/onboarding/workspace-switching development.

## Development Workflow

Use:

**inspect -> one controlled change -> targeted test -> broader/full test
-> desktop UI test -> mobile/responsive UI test -> commit -> checkpoint
at meaningful milestones.**

Prefer direct Windows venv execution:

`.\venv\Scripts\python.exe`

Prefer guarded PowerShell changes when practical.

Do not perform large uncontrolled rewrites.

Keep inspection output small because large PowerShell output is easily
truncated.

The repository and current tests override stale documentation.
