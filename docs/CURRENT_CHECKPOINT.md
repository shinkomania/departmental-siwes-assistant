# DSA Current Checkpoint

> Read this file first when resuming DSA development.

## Project

**Current name:** Departmental SIWES Assistant (DSA)\
**Leading future name:** Digital SIWES Assistant (DSA) --- branding
migration deferred.

## Current Phase

**Phase 4 --- Academic Directory / Platform Admin Review Workflow**

## Verified Test Baseline

**136/136 tests passing**

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

Secured individual Academic Directory Request detail page completed in commit 3971f7e.

Implemented/tested:

- authorized Platform Admin access;
- unauthorized authenticated user receives HTTP 403;
- missing request returns HTTP 404;
- request information renders correctly;
- queue Review details now links to the secured detail page;
- detail page remains intentionally read-only;
- live queue-to-detail browser flow verified;
- full regression suite now passes 136/136 tests.

## Exact Next Task

**Expose Academic Directory Requests from the Platform Administration overview.**

The secured read-only individual DirectoryRequest detail page is complete in commit 3971f7e.

Live browser verification confirmed that the queue and detail page work, but the Platform overview does not yet provide a direct entry to the Academic Directory Request workflow.

Do not combine this navigation improvement with Approve, Reject, More Information, or other review-state mutations.

## First Development Step

Inspect the current Platform Administration dashboard template and the admin dashboard route/context before making changes.

Identify the existing dashboard navigation/card pattern and add the smallest consistent entry that gives Platform Administrators direct access to /admin/directory-requests.

Do not add review-state mutations during this navigation task.

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
