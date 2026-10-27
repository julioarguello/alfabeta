# Specification Quality Checklist: Each subject's content, from Classroom to the family's Drive

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-25
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

- Iteration 1 (2026-10-25): three markers (base folder, organization, the student's Drive). The operator
  changed the approach: Classroom is the source, the family's Drive the target, and the structure
  `<school-year>/<subject>/<topic | month>/<source>/` is common to Classroom and to the books.
- Iteration 2 (2026-10-25): spec rewritten with that approach. Three [NEEDS CLARIFICATION] markers remain:
  FR-012 (what «curso» means: course or school year), FR-013 (name of the topic folder) and story 6 (saving
  the teacher's grades and comments). Constitution amended to 1.0.1 for the same change.
- The spec names some configuration keys and the skill (`full_review_days`,
  `lock_idle_minutes`, `classroom-sync`) because they are the contract the family sees, not
  implementation decisions.
- Iteration 3 (2026-10-25): resolved. «Curso» = school year; the teacher's grades and comments yes,
  next to the replica; topic folder = book topic, with a match proposed by alfabeta and
  confirmed by the family (FR-013). Observing the real Classroom stays as the first task of the
  plan (the student's session had expired).
- The product names that appear (Classroom, Drive, Dropbox, Science Bits, PDF, the desktop
  app) are the domain and the constraints the operator sets, not implementation
  decisions. Language, configuration format and download mechanism are left to the plan.
- The calendar itself is deferred to the calendar epic (out of scope); since 2026-10-26 the accounts it is shared with are a configured list (FR-011b).
- `/speckit-analyze` pass 5 (2026-10-25): the observation of the real Classroom this list asked for is done (research, facts table); that pass's medium findings fixed.
- `/speckit-analyze` passes 6 and 7 (2026-10-25): their high findings fixed (sandbox flow, run identifier, «unchanged» with dates going by, `display_name`, captures from another run). From pass 8 on only critical and high findings are fixed; the medium and low ones left are listed in the spec PR as open.
- `/speckit-analyze` passes 8–11 (2026-10-25): pass 11 ends with no critical or high findings. The open medium and low ones go in the spec PR description.
- Clarification 2026-10-26 (constitution 1.3.0): topic folders and Classroom items carry a `YYYYMMDD` date prefix, `Tema PNN` and the month folders are dropped, and what has no topic goes in `<date> - Sin tema` (FR-012–FR-015). The spec, plan, data model, contracts, quickstart, research and tasks follow it.
- Clarification 2026-10-26 (constitution 1.4.0): several accounts per student. The Drive root is the master of one-way mirrors (FR-011a), and the calendar and the notebooks are shared with a list of accounts each (FR-011b). The spec, plan, data model, contracts and tasks follow it; `/speckit-analyze` has not been re-run on this change.
- Iteration 4 (2026-10-27): User Story 7, reading Classroom with nobody present, without the
  operator's Mac or browser (FR-032 to FR-038, including FR-032a/b and FR-033a; SC-011 to SC-015). The operator decided to amend the
  constitution and use a vault (their words quoted in research R15). Two routes: the token route
  (gpsoauth first-party sign-in token, primary) and the scripted web sign-in (password and
  second-factor seed in the vault, fallback), each gated by a spike (S4, S5, S6) with pass criteria
  in the plan, instead of leaving anything as a `[NEEDS CLARIFICATION]` marker. Three risk-acceptance
  decisions are the family's, to be recorded in the Clarifications when the PR review settles them:
  the custody of the secret by the cloud project's administrators (constitution II names them); the
  terms-of-service risk of automated access to a minor's account; and the blast radius of the
  token-route secret, which is account-wide and bypasses the second factor, so a vault read exposes
  the whole account (FR-032a). Because this amendment weakens NON-NEGOTIABLE principles III and IV,
  the independent review determined (constitution, Development workflow) that it needs the operator's
  explicit request, quoted with its date in the PR, before any merge. Constitution 2.0.0 (MAJOR:
  principle III redefined). `/speckit-analyze` was re-run on this change.
