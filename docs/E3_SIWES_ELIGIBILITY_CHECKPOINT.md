# E3 — Programme-Level SIWES Eligibility Checkpoint

## Status

E3 implementation and regression validation completed.

## Completed Scope

E3 establishes programme-level SIWES eligibility as the boundary for
personal SIWES actions while preserving public placement exploration.

### Public Placement Exploration

The following remain available without a SIWES profile:

- Placement search
- Organization browsing
- Organization detail pages
- General exploration of placement opportunities

Viewing an organization does not require SIWES eligibility.

### Personal SIWES Actions

The following require:

1. Authentication
2. The authenticated user's own StudentProfile
3. A selected academic programme
4. A confirmed SIWES-enabled programme configuration

Personal actions include:

- Saving/bookmarking an organization
- Tracking an application

### SIWES Eligibility States

The programme-level configuration supports:

- Required
- Optional
- No SIWES
- Pending Verification

Required and Optional programmes permit personal SIWES actions.

No SIWES and Pending Verification programmes do not permit personal
SIWES actions.

### Security Boundary

Personal SIWES actions resolve the StudentProfile from the authenticated
session user rather than trusting a manually supplied student/profile ID.

This prevents an authenticated user from switching the active personal
SIWES context to another student's profile.

## Administrative Configuration

Platform administrators can:

- Browse programme-level SIWES configurations
- Create a missing configuration for a programme
- Edit the programme's SIWES status
- Configure duration
- Configure eligible academic level
- Configure timing
- Configure semester information
- Record required forms
- Record special requirements
- Record verification source
- Record verification reference
- Record last verification information

## Validation Completed

### Compilation

The following compiled successfully:

- app.py
- routes/admin.py
- routes/placement.py
- services/siwes_eligibility.py
- models/academic.py
- test_app.py

### Placement Regression

All four existing placement regression tests passed:

- test_placement_search_form
- test_placement_search_results
- test_organization_details
- test_bookmark_and_track_application

### Security Regression

The authenticated-profile security test passed:

- test_legacy_student_id_cannot_switch_authenticated_profile

### Targeted SIWES Behaviour

The targeted E3 SIWES eligibility behaviour tests previously passed:

- Public organization detail remains open
- Required programme can save
- Optional programme can save
- No SIWES programme cannot save
- Pending programme cannot save
- Required programme can track
- Optional programme can track
- No SIWES programme cannot track
- Pending programme cannot track

### Repository Hygiene

- Temporary E3 test removed.
- git diff --check passed.
- No E3 implementation files have been committed yet at this checkpoint.

## Current Git Base

Current HEAD before E3 commit:

2442176 — Add E2.5 academic directory checkpoint

## E3 Working Tree

Expected E3-related changes:

- routes/admin.py
- routes/placement.py
- templates/admin/dashboard.html
- templates/organization.html
- test_app.py
- services/siwes_eligibility.py
- templates/admin/siwes_configuration_form.html
- templates/admin/siwes_configurations.html

## Next Step

Review the checkpoint and then create the controlled E3 commit.

Do not push until the commit and post-commit verification are complete.
