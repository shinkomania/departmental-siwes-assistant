# DSA Current Checkpoint

> Read this file first when resuming DSA development.

## Project

**Current name:** Departmental SIWES Assistant (DSA)\
**Leading future name:** Digital SIWES Assistant (DSA) --- branding
migration deferred.

## Current Phase

**Phase 4 --- Academic Directory / Platform Admin Review Workflow**

## Verified Test Baseline

**133/133 tests passing**

Protect this baseline. Do not treat the old 177-test output as genuine;
that run included duplicate unittest discovery from a backup file whose
filename began with `test_`.

A non-failing SQLAlchemy `Query.get()` LegacyAPIWarning is known
technical debt.

## Last Completed Work

Platform Admin Academic Directory Request queue:

``` text
/admin/directory-requests
```

Implemented/tested:

-   Platform Admin can open queue;
-   default filter shows Submitted requests;
-   filter by status;
-   filter by request type;
-   search academic fields;
-   invalid filters fall back safely.

The six queue tests increased the genuine suite from 127 to 133 tests.

## Exact Next Task

**Build the secured individual Academic Directory Request review/detail
page.**

The current queue template contains a non-functional **Review details**
placeholder and says review actions will be handled from a secured
request review page.

Do not jump directly to Approve/Reject actions.

## First Development Step

Inspect the complete existing request-card section before editing it:

``` powershell
Get-Content "templates\admin\directory_requests.html" |
Select-Object -Skip 165 -First 160
```

Then inspect any current repository state needed to design the detail
route safely.

## Required Security Coverage

Reuse the existing `_create_platform_admin_security_fixture()`.

For the detail/review workflow, explicitly test:

-   authorized Platform Admin access;
-   unauthenticated/unauthorized access;
-   invalid or missing request ID behavior;
-   correct request data rendering.

Do not weaken `@admin_required` or bypass the existing permission
system.

## Critical Data Rule

A `DirectoryRequest` is a review record.

**Approving a DirectoryRequest must not automatically create or verify
Institution, AcademicUnit, Department, or Programme records.**

Authoritative academic-directory changes remain a separate deliberate
operation.

## Development Workflow

**Inspect → one controlled change → targeted tests → regression tests →
checkpoint → proceed.**

Use the current repository as implementation truth and the recovered old
conversation/Master Development Record as historical context.

On Windows, prefer direct venv execution:

``` powershell
.\venv\Scripts\python.exe -m unittest -v
```

## Continuity Rule

After the next meaningful milestone:

-   update this checkpoint;
-   update the Master Development Record if a durable decision/milestone
    changed;
-   commit the documentation with the related project work where
    appropriate.

------------------------------------------------------------------------

**Checkpoint initialized at the clean 133/133 baseline before the
individual directory-request review page implementation.**
