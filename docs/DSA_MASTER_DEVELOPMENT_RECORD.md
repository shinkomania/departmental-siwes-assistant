# DSA Master Development Record

> Living continuity record for the DSA project.\
> This document records durable project decisions and milestones, not
> every chat message.\
> The current repository remains the implementation source of truth.

## 1. Project Identity

**Current repository/project name:** Departmental SIWES Assistant (DSA)

**Leading future brand direction:** Digital SIWES Assistant (DSA)

The project began as a departmental SIWES assistant and later expanded
toward a multi-institution SIWES platform. The DSA identity should be
preserved if the future branding migration proceeds. Do not rename the
repository, code, README, templates, configuration, or public branding
piecemeal. Treat any rename as a deliberate migration after appropriate
brand/name checks.

The product should remain SIWES-focused for now rather than expanding
prematurely into a general NYSC/jobs/internship platform.

## 2. Core Product Purpose

DSA is intended to support the Nigerian SIWES ecosystem across students,
institutions, academic programmes, SIWES coordinators, and placement
organizations.

The original useful features should be preserved and evolved:

-   placement discovery/search;
-   verified and evidence-backed organization information;
-   saved/bookmarked organizations;
-   placement application tracking;
-   SIWES knowledge/guidance;
-   student dashboard;
-   administrative workflows;
-   truthful provenance/verification labels.

The application pipeline concept includes:

Interested â†’ Contacted â†’ Submitted â†’ Interview â†’ Accepted

DSA must not fabricate organization listings or present unverified
submissions as verified facts.

## 3. Development Method

Use this workflow for future development:

**Inspect current state â†’ understand the historical decision/context â†’
make one controlled change â†’ run targeted tests â†’ run regression tests
when appropriate â†’ confirm the checkpoint â†’ proceed.**

Additional rules:

-   Do not blindly reuse an old command when the current repository has
    changed.
-   Historical conversation = intent/history.
-   Current repository = implementation truth.
-   Tests = verification of behavior.
-   Git = durable implementation history.
-   Prefer complete replacement files for corrections when practical.
-   On Windows, avoid depending on PowerShell venv activation because
    execution policy has blocked it before.
-   Prefer direct execution such as:

``` powershell
.\venv\Scripts\python.exe -m unittest -v
```

## 4. Architecture Direction

DSA evolved from a Computer Engineering/department-specific application
into a multi-institution architecture.

Academic hierarchy:

**Institution â†’ AcademicUnit (Faculty/College/School) â†’ Department â†’
Programme**

Programme-level SIWES eligibility is authoritative. Programme SIWES
states include concepts such as:

-   Required
-   Optional / programme-dependent
-   No SIWES
-   Pending Verification

Programme configuration may include:

-   SIWES duration;
-   minimum level;
-   minimum CGPA where applicable;
-   placement type;
-   stipend policy;
-   ITF documentation;
-   supervisor-visit policy;
-   report/defence requirements;
-   academic-calendar window;
-   institution/school letter format.

A student should only create/use the SIWES-specific profile where the
selected programme is SIWES-enabled according to the programme rules.

## 5. Identity, Roles and Authorization

Use one primary User identity, with StudentProfile for student-specific
information.

Administrative authority is role/permission/scope based rather than a
legacy global `is_admin` flag.

Important role concepts include:

-   Platform Administrator;
-   Primary Institution Administrator / Institution Administrator;
-   Institution SIWES Officer;
-   Departmental SIWES Coordinator;
-   other scoped roles where explicitly defined.

Role assignments may be scoped to institution, department, or programme.

Platform-level access must not be weakened or bypassed for convenience.

A reusable Platform Administrator security fixture exists in the test
suite and should be reused for admin security tests rather than
inventing temporary authorization structures.

## 6. Security Foundation

Phase 2 formally established the major
authentication/authorization/security foundation. At its completion, the
historical checkpoint was **112 tests passing**.

Implemented security-foundation concepts included:

-   unified user authentication;
-   password hashing;
-   active/inactive account enforcement;
-   student profile ownership tied to authenticated users;
-   removal of legacy `student_id` session authority;
-   removal of legacy `is_admin` authority;
-   explicit role + permission + scope authorization;
-   institution/department/programme-scoped access;
-   protected privileged role application/review flows;
-   self-approval prevention;
-   Platform Administrator bootstrap;
-   CSRF protection on state-changing requests;
-   authenticated organization contribution;
-   safe logout/session clearing;
-   safe redirect handling;
-   production SECRET_KEY enforcement;
-   secure production cookie defaults;
-   tracked-secret review.

Later security work may still include email verification, password
reset, rate limiting, finer-grained action permissions, organization
review workflow, and deployment hardening.

## 7. UI and Branding Direction

Phase 3 moved into UI/branding after the security foundation.

Persistent design requirement:

**DSA should look top-notch, highly user-friendly, modern, professional,
and coherent across the application.**

Design changes should be systematic and shared through common
layout/design components rather than inconsistent page-by-page styling.

Historical branding included DSA with subtle **Powered by
ShinkomaniaPlug** identity.

Do not allow UI modernization to weaken authorization or data-integrity
rules.

## 8. Academic Directory Principles

The academic directory is controlled/authoritative data.

Students/users may request missing directory information, but a request
is a review record --- not an authoritative academic record.

A directory request must never automatically create or verify:

-   Institution;
-   AcademicUnit;
-   Department;
-   Programme.

This remains true even when a DirectoryRequest is marked Approved.
Approval of the request and deliberate creation/verification of
authoritative academic records are separate operations.

Supported request types currently include:

-   Institution
-   Programme

DirectoryRequest workflow statuses include:

-   Submitted
-   Under Review
-   More Info Required
-   Approved
-   Rejected
-   Withdrawn

Open states are Submitted, Under Review, and More Info Required.

Final states are Approved, Rejected, and Withdrawn.

Duplicate open requests are prevented according to the implemented
matching rules.

## 9. Platform Admin Academic Directory Queue

The Platform Admin queue exists at:

``` text
/admin/directory-requests
```

The queue currently supports:

-   default Submitted status view;
-   status filtering;
-   request-type filtering;
-   search across relevant academic fields;
-   safe fallback for invalid filters;
-   chronological ordering.

The queue is protected by the existing Platform Admin authorization
mechanism.

The current queue template intentionally contains a non-functional
**Review details** placeholder and states that review actions will be
handled from a secured request review page.

That placeholder identifies the next implementation boundary.

## 10. Current DirectoryRequest Model Safeguard

The DirectoryRequest model contains review-state helpers such as:

-   `mark_under_review(...)`
-   `approve(...)`
-   `reject(...)`
-   `request_more_information(...)`
-   `withdraw()`

These state helpers do not grant permission to automatically create
authoritative academic directory records.

Any future review action must preserve authorization, state integrity,
reviewer identity, notes/timestamps as appropriate, and the separation
between request decisions and authoritative data creation.

## 11. Official Communication System

Official notices are part of the DSA architecture.

They should support targeting such as:

-   institution-wide;
-   department;
-   programme;
-   level;
-   SIWES session;
-   selected group.

Only authorized staff roles may publish official notices.

Institution notices may be issued by the Primary Institution
Administrator or an authorized Institution SIWES Officer.

Departmental notices may be issued by authorized Departmental SIWES
Coordinators within their own scope.

Notice concepts include:

-   title;
-   message;
-   author and role;
-   scope;
-   publish date;
-   expiry date;
-   optional attachment;
-   priority;
-   Draft / Published / Archived status;
-   clear labels such as Official Institution Notice or Official
    Department Notice.

Students cannot create official notices.

Community/group chat is deferred. A later implementation should prefer
official DSA communities/channels rather than unrestricted user-created
groups.

## 12. Organization Data Integrity

Organization information must remain truthful and provenance-aware.

Distinguish concepts such as:

-   verified organization information;
-   online research results;
-   student/community submissions.

A user saying an organization accepts SIWES students must not
automatically turn that statement into verified placement data.

The architecture should eventually maintain a controlled
submission/review path before community-provided information becomes
authoritative.

## 13. Testing History and Current Baseline

Important historical checkpoints:

-   Phase 2 security foundation: **112 tests passing**
-   Before the six Platform Admin directory queue tests: **127 tests
    passing**
-   Current verified clean baseline: **133 tests passing**

A temporary backup named with a `test_` prefix was once auto-discovered
by unittest and caused an apparent **177-test** run. That was duplicate
discovery, not a genuine increase in the suite.

The backup was renamed so it would not be discovered.

**Protected current baseline: 133/133 passing.**

A SQLAlchemy `Query.get()` LegacyAPIWarning has appeared. It is
non-failing technical debt and should not derail the current Phase 4
work.

## 14. Current Phase

**Phase 4 --- Academic Directory / Platform Admin Review Workflow**

Already implemented and tested:

-   student missing-institution request submission;
-   student missing-programme request submission;
-   authentication requirement;
-   verified/selectable institution requirement for programme requests;
-   duplicate-open-request prevention;
-   academic hierarchy/profile validation;
-   Platform Admin request queue;
-   queue status filtering;
-   queue request-type filtering;
-   queue search;
-   invalid-filter fallback.

The six queue tests brought the suite from 127 to the current 133 tests.

A separate explicit unauthorized-access test for the new review/detail
workflow should be included as security coverage; earlier planning
mentioned unauthorized access, but the six queue tests themselves did
not add a distinct unauthorized queue-access test.

## 15. Exact Unfinished Task

The next implementation task is:

**Build the secured individual Academic Directory Request review/detail
page.**

Do not jump directly into all status-changing actions.

Recommended sequence:

1.  Inspect the current queue-card markup and relevant admin
    route/template structure.
2.  Add a secured detail route/page for an individual DirectoryRequest.
3.  Show the submitted information, requester context,
    evidence/reference, notes, status, reviewer/review metadata as
    appropriate.
4.  Add tests for authorized access, invalid/missing request handling,
    and unauthorized access.
5.  Run targeted tests.
6.  Run the full regression suite and establish the new baseline.
7.  Only after the detail page is stable, implement controlled workflow
    actions:
    -   Under Review
    -   More Info Required
    -   Approve
    -   Reject
8.  Keep request approval separate from authoritative academic-record
    creation.

## 16. Naming Decision

The leading future naming direction is:

**DSA --- Digital SIWES Assistant**

Possible positioning:

*An intelligent SIWES support platform connecting students, institutions
and industry.*

The original Departmental SIWES Assistant name remains part of the
product origin story.

No repository/code rename has been authorized yet. A future rename
should be performed as a deliberate branding migration after appropriate
name/brand checks.

## 17. Continuity Protocol

At every meaningful milestone, update:

1.  `docs/DSA_MASTER_DEVELOPMENT_RECORD.md` --- durable decisions,
    architecture and milestone history.
2.  `docs/CURRENT_CHECKPOINT.md` --- concise exact current state and
    next action.

Do not turn either file into a raw chat transcript.

For a future ChatGPT conversation, provide these files (or make them
available in the Project) and instruct ChatGPT to read them before
development.

The repository and current test results always override stale
documentation if they disagree.

------------------------------------------------------------------------

**Record initialized from the recovered historical DSA development
conversation and the verified current checkpoint.**

------------------------------------------------------------------------

## 18. Directory Review Workflow Through Milestone A

The Academic Directory Request workflow has progressed substantially
beyond the earlier 133-test checkpoint.

Completed capabilities now include:

- secured Platform Administrator request detail/review;
- controlled review claiming and ownership;
- approval and rejection;
- More Info Required clarification workflow;
- requester responses with chronological history;
- reviewer ownership preservation after requester response;
- requester withdrawal for open requests;
- student request list/detail experience;
- state-aware Profile Academic Directory Support.

The authoritative-directory invariant remains unchanged:

**DirectoryRequest approval is review state only. It does not
automatically create, publish, activate, or verify authoritative academic
directory records.**

Authoritative directory publication remains a separate future Platform
Administration operation.

### Review Ownership

Review ownership intentionally remains lightweight.

A Submitted request begins in the general queue. Once a Platform
Administrator begins review, the request is assigned to that reviewer.
Only that reviewer may perform controlled review actions.

When clarification is requested and the requester responds, the request
returns to Under Review while remaining assigned to the same reviewer.

A future release/reassign capability may be introduced if operational
need justifies it, but it is not required for the current workflow.

### Withdrawal Semantics

DirectoryRequest withdrawal and authoritative-record deactivation are
different concepts.

A requester may withdraw an open request.

An approved request should not later be rewritten as Withdrawn merely
because an authoritative record is eventually suspended or deactivated.

Authoritative records must own their own lifecycle independently of the
historical review record.

## 19. Directory Request Eligibility and Profile Cleanup

Milestone A was completed in commit:

`8654703 Enforce directory request eligibility and streamline profile support`

The full regression suite passed:

**223 tests**

Eligibility rules now include:

- maximum one open DirectoryRequest per user;
- Submitted, Under Review, and More Info Required are open states;
- final request states do not permanently block future eligible requests;
- an already-linked structured programme blocks the normal
  missing-Institution/missing-Programme workflow;
- Programme requests require an appropriate authoritative Institution;
- eligibility is enforced server-side.

The Student Profile Academic Directory Support interface is state-aware:

- eligible/unlinked;
- open request;
- linked academic directory.

The previous duplicate Profile request experience was consolidated.

Desktop and 390x844 mobile UI verification passed for all important
states.

No migration was required for this milestone.

## 20. Account, Student Profile, and Staff Authority Architecture

DSA will use a single account identity model rather than permanently
separate Student and Staff accounts.

The durable distinction is:

- `User` - identity/account;
- `StudentProfile` - optional student academic context;
- staff-role application - request for institutional authority;
- `UserRoleAssignment` - approved authority.

A DSA account does not automatically imply that the person is a student.

Future onboarding should ask the person's immediate purpose, such as:

- Student;
- SIWES Staff / Coordinator.

The Student path creates a StudentProfile.

The staff path uses **Request Staff Access** and must not force lecturers
or coordinators through student-specific fields.

A user who initially joins as a student may later request staff access if
they genuinely hold an official SIWES responsibility. This does not
require a second DSA account.

A person may legitimately hold both a StudentProfile and one or more
approved scoped roles.

This should be represented through workspace switching rather than
duplicate accounts.

Staff-role authority must always be separately verified and scoped.

Platform Administrator is not a self-requestable role.

## 21. Workspace and Platform Authority Direction

Future multi-role accounts should use explicit workspace context.

Examples:

- Student Workspace;
- Departmental SIWES Coordinator Workspace;
- Institution Workspace;
- Platform Administration.

The interface should eventually expose permission-aware
**Switch Workspace** behavior rather than relying on a generic permanent
Admin button.

High-authority actions must remain auditable by actor, action, scope,
time, and reason where appropriate.

The Primary Platform Administrator / Platform Owner is the highest
platform authority, but this must be represented by roles/permissions
rather than hard-coding a person's name.

Delegated platform aides should receive only the permissions they need.

Examples:

- Organization Review Officer;
- User & Access Administrator.

Use least privilege.

## 22. Notification and Evidence Direction

A reusable Notification System should be centered on `User`, not
StudentProfile, so it can serve students, reviewers, institution staff,
coordinators, and Platform Administrators.

Notifications should eventually support:

- unread/read state;
- category/source;
- title/message;
- timestamp;
- direct action destination.

Directory clarification responses are an early example of an event that
should later generate an actionable reviewer notification.

Evidence remains supporting material and must never automatically verify
or publish academic records.

A future reusable evidence architecture should support reference URLs,
attachments, and supporting notes without adding ad-hoc fields such as
attachment1, attachment2, and so on.

This evidence subsystem is deferred until its proper milestone.

## 23. Next Development Milestone

The next milestone is:

**Reviewer Case Workspace**

The admin review page must evolve from a static request/review page into
a clear case workspace containing:

1. Request Summary.
2. Chronological Review Conversation.
3. Current Review State.
4. Derived Response Received cue when appropriate.
5. Assigned reviewer context.
6. A clean Decision Panel containing only valid actions.

The requester clarification is already persisted correctly; the current
gap is primarily reviewer presentation and workflow visibility.

Do not introduce a new persisted "Response Received" request status
unless implementation inspection demonstrates a real need.

After Reviewer Case Workspace, the planned sequence is:

1. Reusable DSA Notifications Foundation.
2. Platform Administration refresh.
3. Controlled Directory Publication.
4. Staff Access Requests and scoped workspaces.
5. General account/profile/onboarding/workspace-switching experience.

At this checkpoint the verified implementation baseline is commit
`8654703` with **223 passing tests**.

## 24. Reviewer Case Workspace Completion

Milestone B was completed in commit:

`06bd46f Add directory request reviewer case workspace`

The Platform Administrator directory-request review page now functions
as a case workspace rather than a static request detail page.

It includes:

- chronological clarification conversation;
- clear Reviewer and Requester identity;
- supporting clarification references;
- assigned reviewer context;
- derived Response received state;
- responsive review decision controls.

Response received is intentionally derived from existing state rather
than persisted as another DirectoryRequest status. It applies when the
request is Under Review and the latest clarification message was
authored by the Requester.

Reviewer ownership remains unchanged when a requester responds.

The Decision Panel supports:

- Request More Information;
- Approve Request;
- Reject Request.

Approval remains separate from authoritative academic directory
publication. No review action silently creates or verifies an
Institution, AcademicUnit, Department, or Programme.

Verification at this milestone:

- 4 focused Reviewer Case Workspace tests passed;
- 44 directory-request regression tests passed;
- 227 full-suite tests passed;
- desktop UI passed;
- 390 x 844 mobile UI passed.

The mobile footer was also inspected and confirmed to render correctly;
no footer redesign was required.

The known SQLAlchemy `Query.get()` LegacyAPIWarning remains non-failing
technical debt.

## 25. Reusable Notifications Milestone Direction

The next milestone is:

**Reusable DSA Notifications Foundation**

Notifications must be user-centered and reusable across roles and
workspaces.

A notification should be capable of representing:

- recipient User;
- read/unread state;
- category/type/source;
- title;
- message;
- creation timestamp;
- direct action destination.

Notification links provide navigation only. Authorization must still be
enforced by the destination route.

The first real integration should build on the completed directory
clarification workflow: when a requester responds to a clarification,
the assigned reviewer should be able to receive an actionable
notification linking to the Reviewer Case Workspace.

The architecture must remain suitable for later official notices,
placement activity, coordinator interventions, SIWES deadlines,
supervisor activity, staff-access workflows, and other institutional or
Platform Administration events.

Do not implement notifications as special-purpose fields on
DirectoryRequest.

The implementation baseline entering this milestone is commit
`06bd46f` with **227 passing tests**.

## 26. Reusable DSA Notifications Foundation - Completed

Milestone C established notifications as a reusable platform-level DSA
capability rather than a directory-request-specific feature.

Implementation commit:

`5714446 Add reusable user notification system`

A reusable `Notification` model, migration, notification service,
global notification routes, responsive notification centre and signed-in
header bell were implemented.

Notifications belong to `User`, not `StudentProfile`, allowing the same
system to support students, coordinators, institution officers,
delegated Platform Administrators and other legitimate future roles.

The model supports recipient, category, notification type, title,
message, priority, internal action URL, generic source metadata,
`read_at`, and creation timestamp.

Read state is derived from `read_at`.

The reusable notification service centralizes creation, inbox queries,
unread counts and read operations.

A hard recipient-isolation security contract was established:

**User A must never be able to view, count, mark as read, open, or
bulk-modify User B's notifications.**

This boundary is enforced at service and HTTP-route level.

Platform Administrator authority does not itself provide access to
another user's private notification inbox.

Inactive accounts cannot use stale sessions to access notification
routes.

Notification action URLs are navigation only and do not grant
authorization at their destination. The current service accepts only
controlled internal DSA paths.

The global signed-in interface now provides a notification bell and
unread badge. The notification centre provides unread/total summaries,
category and priority cues, unread state, timestamps, contextual
actions, individual read actions, Mark all as read, and a polished empty
state.

Desktop and 390 x 844 mobile layouts were manually validated.

Temporary development notifications were used to validate the populated
state, priority badges, action controls, bell count and persisted read
transition. The temporary records were removed afterward.

Verification at completion:

- 246 full-suite tests passed;
- 7 focused HTTP notification/security tests passed;
- Python compilation checks passed;
- `git diff --check` reported no whitespace errors;
- desktop UI passed;
- 390 x 844 mobile UI passed;
- populated and read-state UI behavior passed.

Pagination is intentionally deferred but should be added before
production-scale notification volume.

Notification preferences, category muting, external email/push/SMS
delivery, batching/digests, WebSockets and richer analytics remain
future work.

The next step is Milestone C4: connect real directory-review workflow
events to the reusable notification system, beginning with clarification
requested, requester response received, approval and rejection.

Directory review state remains separate from authoritative directory
publication. Notifications must not weaken that invariant.
