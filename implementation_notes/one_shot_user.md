# One-Shot Port User Notes

## Approved Goal

Fully implement pychete's one-shot Matchete-style one-loop matching port on the
`one-shot-port` branch. The objective is to make pychete capable of performing
one-loop EFT matching for the Matchete validation target models, especially
SMEFT UV-complete matching models, while preserving pychete's Pythonic API and
using Symbolica/idenso/spenso/vakint as the computational backends instead of
reimplementing symbolic physics algorithms in Python.

Very important: use Symbolica as much as possible and periodically rescan the
Symbolica Python stub files so the native API stays in context.

Normal pychete tests must be Mathematica-independent. pytest must never require
Mathematica, `wolframscript`, or a runnable Matchete installation. Development
helper Wolfram scripts may load the read-only Matchete checkout to generate
committed pychete-owned fixtures, but runtime code and tests must load only
those fixtures.

Keep the approved implementation plan copied into both
`implementation_notes/one_shot_user.md` and
`implementation_notes/one_shot_implementation.md`, and keep both copies updated
whenever the plan changes. Keep `one_shot_implementation.md` continuously
updated with current progress, completed milestones, test status, backend/API
discoveries, dependency patches, blockers, and remaining work.

## Approved Plan

# One-Shot One-Loop Matching Port

## Summary

- Build a Pythonic pychete implementation of Matchete-style one-loop matching,
  prioritizing the default SMEFT UV matching models first, then all Matchete
  validation tests that map cleanly to pychete's architecture.
- Normal pytest must be Mathematica-independent. Development-only Wolfram
  scripts may load Matchete to generate serialized pychete fixtures under the
  repo, but tests load only those committed fixtures.
- Use Symbolica as the symbolic engine, idenso/spenso for gamma, colour,
  metric, and tensor algebra. Use pychete's own Matchete-style analytic backend
  for one-loop vacuum integral evaluation after tensor reduction, including
  single-scale, zero-mass, and mixed-mass cases. Use vakint for
  topology-independent tensor reduction and as an optional supported backend or
  cross-check for single-scale massive analytic evaluations.
- Compare results by pychete canonical equality, backed by Symbolica evaluator
  numeric probes for hard-to-canonicalize expressions.

## Key Changes

- Add `helper_mathematica_scripts/` with Wolfram scripts that load Matchete and
  export model definitions, validation expected outputs, supertraces, matching
  conditions, and selected unit-test fixtures into pychete-owned serialized
  assets. Keep optional top-level `scripts/` wrappers checked in for users who
  have Mathematica and want a convenient export/convert entry point, while
  keeping the maintained helper implementation and all normal pytest/runtime
  paths Matchete- and Mathematica-independent.
- Treat the direct Python Mathematica loader as a documented supported-subset
  loader for simple declarative model assets and saved-result snippets only.
  For complicated Mathematica models, use Wolfram/Matchete helper scripts to
  load the model, extract Matchete's parsed internal data, and emit equivalent
  pychete serialized state or Python fixture files that can be committed and
  used by tests and users.
- Add committed fixture assets for Matchete-independent pytest validation;
  never require `wolframscript` in normal tests.
- Extend pychete metadata with gauge groups, representations, CG tensors,
  charges, chiral fermions, ghosts, Goldstones, background fields, coupling
  symmetries, diagonal/unitary metadata, and SMEFT basis metadata using
  Symbolica symbol tags/data.
- Replace the current tiny Mathematica loader as the path for complex
  validation models with fixture loading; keep direct Mathematica-input support
  explicitly secondary and limited to its documented subset.

## Matching Engine

- Add a one-loop matching API around `Theory.match(..., loop_order=1)` returning
  a structured `MatchingResult` with UV Lagrangian, fluctuation operators,
  individual supertraces, off-shell EFT Lagrangian, on-shell EFT Lagrangian, and
  matching conditions.
- Implement the Matchete pipeline in pychete terms: free Lagrangian
  construction, Feynman rules/functional derivatives, fluctuation-operator
  extraction, heavy/light DoF classification, propagator expansion, supertrace
  generation, loop-momentum tensor reduction, integral evaluation, EFT
  truncation, EOM/on-shell reduction, and effective-coupling mapping.
- Use Symbolica patterns, `replace_multiple`, `series`, `coefficient`,
  `collect`, `derivative`, `Transformer`, and evaluator APIs before adding
  Python traversal logic.
- Route gamma/colour/metric simplification through idenso adapters,
  tensor/CG contraction through spenso adapters, topology-independent tensor
  reduction through vakint where useful, one-loop analytic vacuum-integral
  evaluation through a pychete-owned Matchete-style backend, and supported
  single-scale massive cross-checks through vakint adapters.
- If idenso/spenso/vakint are insufficient, add patch files under
  `dependencies/patches/`, make `dependencies/install_dependencies.py` apply
  them after clone/reset and before build, and test the patched behavior from
  Python.

## Validation And Tests

- First green milestone: fixture-generation scripts plus committed fixtures for
  the default integration models: `VLF_toy_model`,
  `Singlet_Scalar_Extension`, `E_VLL`, and `S1S3LQs`.
- Then port mappable unit validations for definitions, covariant derivatives,
  EFT counting, Feynman rules, loop integration, Dirac/NCM algebra,
  simplifications, coupling manipulation, flavor/group/CG behavior, SSB, and
  dimensional reduction.
- Exclude tests that only assert Matchete's internal structure, caching,
  package globals, print forms, or Mathematica-specific behavior with a
  documented skip map.
- For every symbolic equality test, canonicalize with
  pychete/Symbolica/idenso/spenso/vakint; where canonical equality is fragile,
  add Symbolica `Evaluator`-based numeric probes with deterministic sample
  points.
- Keep `pytest` and `mypy` green at each committed milestone.

## Workflow

- During implementation, create and maintain
  `implementation_notes/one_shot_user.md` and
  `implementation_notes/one_shot_implementation.md`.
- Commit and push only green, coherent milestones to remote branch
  `one-shot-port`.
- Preserve the existing public API discipline: intended user APIs are exported
  through `pychete.api` and package root `pychete`, with docstrings and Jupyter
  `_repr_html_` / `_repr_latex_` where relevant.

## Assumptions

- Public API should remain Pythonic pychete, with Matchete-inspired helpers only
  where they reduce friction.
- Pytest must not depend on Mathematica, Matchete runtime loading, or
  `wolframscript`.
- Full validation means "all tests that map to pychete's implementation model,"
  with one-loop SMEFT matching treated as the primary acceptance target.

## Additional User Decisions

- Keep the Mathematica conversion route as an optional committed convenience
  for users who have Mathematica, preferably through a top-level `scripts/`
  directory. This does not change the core rule: pychete runtime code and
  pytest remain completely Matchete- and Mathematica-independent, and committed
  pychete-owned fixtures are the normal validation/user artifacts.
- Keep both the loaded-model-state conversion route and the previous
  matching-result conversion route discoverable under the top-level `scripts/`
  directory. The maintained implementation can still live under
  `helper_mathematica_scripts/`, but the user-facing convenience wrappers
  should stay committed with pychete.
- Continue treating the top-level Mathematica conversion scripts as optional
  convenience tooling only. It is acceptable to improve those scripts so users
  with Mathematica can generate pychete-owned fixtures, but runtime pychete and
  pytest must remain independent of Matchete and Mathematica.
- Keep a one-command optional Wolfram entry point under top-level `scripts/`
  for users who want Mathematica to perform the loaded-model export and then
  invoke pychete's fixture converter. This is a convenience wrapper only; the
  committed fixtures remain the canonical pychete inputs for users/tests
  without Mathematica.
