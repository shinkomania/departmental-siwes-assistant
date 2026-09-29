# DSA CURRENT CHECKPOINT

## Current Repository State

Project:

**DSA - currently Departmental SIWES Assistant**
Leading future brand direction: **Digital SIWES Assistant**

Branch:

`phase4-programme-siwes-config`

Latest implementation commit:

`8654703 Enforce directory request eligibility and streamline profile support`

Milestone A - **Directory Request Eligibility + Profile Cleanup** - is complete.

Verified full regression baseline:

**223 tests passing**

No migration was added for Milestone A.

At the time this checkpoint was prepared, the implementation working
tree was clean immediately after commit `8654703`.

## Completed Directory Request Workflow

The Academic Directory Request workflow currently supports:

- student submission of Institution and Programme requests;
- Platform Administrator review queue;
- secured individual review/detail page;
- reviewer ownership/claiming;
- Under Review workflow;
- More Info Required workflow;
- requester clarification responses;
- approval;
- rejection;
- requester withdrawal of open requests;
- chronological clarification history on the student side;
- ownership-safe student request access.

Review ownership remains lightweight:

- Submitted requests begin in the general review queue;
- a Platform Administrator claims a request by beginning review;
- only the assigned reviewer may perform controlled review actions;
- clarification responses return the request to Under Review while
  preserving the assigned reviewer.

## Critical Directory Invariant

A `DirectoryRequest` is a review record.

Approval does **not** automatically create, publish, activate, or verify
an Institution, AcademicUnit, Department, or Programme.

Authoritative academic-directory publication remains a separate,
deliberate Platform Administration operation.

## Milestone A Rules Now Enforced

Directory-request eligibility now enforces:

- one user may have at most one open DirectoryRequest at a time;
- Submitted, Under Review, and More Info Required count as open;
- final request states do not permanently block a future eligible request;
- a student whose structured `programme_id` is already linked cannot use
  the normal missing-directory workflow to request another Institution
  or Programme;
- Programme requests require an appropriate authoritative Institution;
- server-side enforcement is authoritative; UI hiding is not relied upon
  for security or correctness.

Changing an already-established academic identity must eventually use a
separate profile correction/change workflow rather than abusing the
missing-directory request workflow.

## Student Profile Directory Support UI

The duplicate Academic Directory experience on `/profile` has been
consolidated into a state-aware Academic Directory Support component.

States:

1. Eligible/unlinked:
   - Request Missing Record;
   - My Directory Requests;
   - expandable directory submission workspace.

2. Open request:
   - Directory request in progress;
   - request type and status;
   - View Active Request;
   - My Directory Requests;
   - no second submission workspace.

3. Structured programme linked:
   - Academic directory linked;
   - My Directory Requests;
   - no normal missing-record request action.

The profile account message is also state-aware:

- existing StudentProfile -> Account-linked profile;
- no StudentProfile -> No student profile yet.

The no-profile message explicitly avoids implying that every DSA account
must be a student account.

## UI Verification Completed

Milestone A was manually verified on desktop and mobile.

Verified states:

- eligible/unlinked - desktop PASS;
- eligible/unlinked - 390x844 mobile PASS;
- active directory request - desktop PASS;
- active directory request - 390x844 mobile PASS;
- linked programme/no active request - desktop PASS;
- linked programme/no active request - 390x844 mobile PASS.

The Profile directory workspace received scoped responsive styling
without changing generic directory-request card behavior.

## Identity and Access Architecture Decision

DSA should use **one user account with multiple separately controlled
profiles/roles**, not permanently separate Student and Staff accounts.

Core distinction:

- `User` = account identity;
- `StudentProfile` = optional student/academic context;
- staff-role application = request for institutional authority;
- `UserRoleAssignment` = approved authority.

Registration should eventually lead to a purpose-based onboarding step
such as:

**How will you use DSA?**

Primary paths:

- Student -> create Student Profile;
- SIWES Staff / Coordinator -> Request Staff Access.

A lecturer/coordinator choosing the staff path must not be forced through
student matriculation, level, placement-preference, or other
student-profile fields.

A user who initially creates a Student Profile may later request staff
access if they genuinely hold an official SIWES responsibility.

Student status must not automatically grant staff authority, and staff
authority must not automatically create a StudentProfile.

## Staff Access Direction

Use the terminology:

**Request Staff Access**

rather than presenting ordinary users with a generic "Apply for a role"
experience.

Staff access is for lecturers or other authorized institutional
personnel who already hold an official SIWES responsibility.

Requested roles require verification before authority is granted.

Platform Administrator must never be self-requestable.

A user may legitimately hold both:

- Student Profile;
- approved scoped staff role.

Such users should eventually use **Switch Workspace** rather than
separate accounts.

Possible workspaces include:

- Student Workspace;
- Departmental SIWES Coordinator Workspace;
- Institution Workspace;
- Platform Administration.

Actions must remain permission- and scope-controlled and auditable.

## Platform Authority Direction

The intended initial highest authority is the Primary Platform
Administrator / Platform Owner.

Do not hard-code a person's name into the authority model.

The Primary Platform Administrator may eventually delegate specific
platform permissions to aides without making every aide a full root
administrator.

Examples include:

- Organization Review Officer;
- User & Access Administrator.

Use permission-based delegation and least privilege.

Global Platform Administration authority should permit support across
scopes without pretending that the Platform Administrator is actually a
member of every institutional or departmental role.

## Notifications Direction

A reusable DSA Notification System is planned around the `User`
recipient rather than StudentProfile.

Future notification data should support:

- unread/read state;
- category/source;
- title/message;
- timestamp;
- direct action destination.

It should support students, Platform Administrators, institution staff,
coordinators, and future scoped roles.

## Evidence Direction

Current directory-request evidence remains text/reference based.

Future evidence should support reusable evidence items such as:

- official/reference URL;
- document/image attachment;
- supporting note.

Evidence is supporting material only and must never automatically verify
or publish an academic-directory record.

Do not implement this evidence subsystem as part of the current review
workspace milestone.

## Next Milestone

**Milestone B - Reviewer Case Workspace**

The current problem to solve:

Requester clarification responses are correctly stored and displayed on
the student side, but the Platform Administrator review detail page does
not yet present the full clarification conversation clearly.

The Reviewer Case Workspace should provide:

1. Request Summary.
2. Chronological Review Conversation.
3. Clear current review state.
4. Derived "Response received" cue when the latest relevant
   clarification is from the requester.
5. Assigned reviewer context.
6. Clean Decision Panel for the actions valid in the current state.
7. Existing review ownership enforcement preserved.

Do not create a new database status merely for "Response received".
Derive it from the existing request/message state unless inspection
proves a persisted field is required.

## Planned Sequence After Milestone B

1. Reusable DSA Notifications Foundation.
2. Platform Administration dashboard/navigation refresh.
3. Controlled Directory Publication.
4. Staff Access Requests and scoped workspace development.
5. Broader account/profile/onboarding/workspace-switching experience.

This order may be adjusted when implementation dependencies require it,
but do not silently collapse approval and authoritative publication.

## Development Workflow

Use:

**inspect -> one controlled change -> targeted test -> broader/full test
-> desktop UI test -> mobile/responsive UI test -> commit -> checkpoint
at meaningful milestones.**

Prefer direct Windows venv execution:

`.\venv\Scripts\python.exe`

Prefer guarded PowerShell changes when practical.

Do not perform large uncontrolled rewrites.

The repository and current tests override stale documentation.

## Current Test Baseline

At commit `8654703`:

**223 tests passed in the full unittest suite.**

Known non-failing warning:

SQLAlchemy `Query.get()` is a legacy API under SQLAlchemy 2.x and should
eventually migrate toward `Session.get()`. It is not a blocker for the
current milestone.

## Immediate Next Step

Before modifying Milestone B code, inspect:

- `routes/admin.py` directory-request detail/review routes;
- `templates/admin/directory_request_detail.html`;
- `models/directory_request.py`;
- clarification-message model/relationship;
- directory-request review service;
- current review ownership tests;
- current admin review/detail tests.

Then define the smallest Reviewer Case Workspace change and its targeted
tests before implementation.