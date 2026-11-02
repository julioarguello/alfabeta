# Specification Quality Checklist: Classroom read on the Mac with no app open, signed in from the phone

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-02
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- The first draft's one marker (FR-001: the Mac or a dedicated machine at home) was answered by the
  operator on 2026-11-02 and is recorded under Clarifications: the read runs on the Mac, as
  constitution IX stands; the link reaches it from the phone through a remote view.
- An independent review of the first draft found six blocking findings; this version answers them:
  the measured table now says only what the repo records, with what is not measured listed for the
  plan's spikes; the notice channel is an email from a `family` account that spec 004 now allows;
  the amendments the read needs (constitution Technical constraints, spec 001 FR-006, spec 004
  FR-004 and FR-005) are made in the same pull request; the scope no longer contradicts FR-001; the
  sign-in window is not driven by alfabeta, and the guard covers the whole read; and a per-student
  switch says which read `[schedule]` starts.
- A second independent analysis found no critical or high finding and three medium ones, all answered
  here: the session's life is no longer stated as an absolute hour (R16 saw one last 2 h 47 min);
  the constitution names the two secrets spec 006 adds on the Mac; and the read starts as soon as
  the sign-in window's address reaches Classroom, instead of waiting for the window to be closed.
  Its five low findings are answered too (spec 001 FR-021a, R17, spec 004's role, FR-005's pages,
  and two more items not measured).
- The amendment of 2026-11-02 adds the four `classroom` commands (FR-021 to FR-024), the five seams
  that keep them off macOS-only assumptions (FR-025, SC-007) and how each credential arrives
  (FR-026), at the operator's request for a command-line tool that runs on the Mac today and could
  run elsewhere later, aligned with the peer project.
- The table "What was measured before writing this" names what each fact was observed with, as in
  spec 005. The requirements name the services the family uses (their Google account, a remote view
  through it) and the existing alfabeta pieces they build on, not how they are called. The one
  product named, Chrome Remote Desktop, is in Assumptions as the family's own Google service.
- The peer project lifecoderua/classroom-advisor (MIT) is a reference for the pattern; nothing of it
  is a measurement of this account, and FR-004 requires the allowlist to be recorded here first.
