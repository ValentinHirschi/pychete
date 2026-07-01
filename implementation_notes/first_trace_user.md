# First Trace User Prompt Trail

## Initial Request

We will now proceed with the next major step for pytchete: we want to be calculate the one-loop matching contributions for the VLF toy model.

For this part of the implementation store my prompts in `./implementation_notes/first_trace_user.md` and keep all your progress up to data at all times in `./implementation_notes/first_trace_implementation.md`.

The general outline of what we need is to be able to determine functional fluctuation operators from the UV Lagrangian, construct the relevant logarithmic and power-type functional traces, expand out propagators in the hard-region, and act with covariant derivatives through the resulting functional expression. This also requires being able to evaluate derivatives acting on Wilson lines.

As a starting point, do a **Very deep dive** into the Matchete source material. The majority of this machinery is found in Package/Matching.m, Package/SuperTrace.m, but also look for dependencies to other package files. Some of the machinery, e.g., that for determining loop momenta counting in the fluctuation operators and supertraces are not really needed for matching the toy model, but keep in mind that we will aim for parity of capability in the medium term. In this deep dive, you will pay particular attention to architecture questions, and you will ask the user clarifying questions to guide the implementation. Generally speaking, we will wish to avoid the global variables used in the original Matchete and prefer passing the information around with bespoke (class) objects.

## Clarification Prompt

Please elaborate on the meaning of "Introduce an explicit immutable matching context that replaces Matchete globals: field degrees of freedom, heavy/light type classes, inferred masses, gauge couplings, fluctuation operators, X-term EFT/order metadata, and trace inventory."

## Goal Statement Prompt

OK before you implement the plan, give me a "goal statement" that details all milestones and which I can assign you as goal after you started the implementation of the plan.

## Implementation Request

PLEASE IMPLEMENT THIS PLAN:

# VLF One-Loop Functional Matching

## Summary

Implement full off-shell one-loop matching for the VLF toy model through EFT dimension 6, with machinery parameterized by `eft_order` for higher orders. The result should include log-type and power-type traces, explicit pole terms, and finite `LF` loop-function placeholders, without on-shell reduction or Greens-style output simplification.

At implementation start, create and maintain:
- `implementation_notes/first_trace_user.md`
- `implementation_notes/first_trace_implementation.md`

## Key Changes

- Add central loop/matching symbols in `SymbolStore`: ordered functional product, open covariant derivatives, propagators, loop momenta, `LFFull`, finite `LF`, epsilon, hbar, Wilson-line terms, X/M/gauge insertion heads, plus hybrid spinor helpers `Transp`, `GammaCC`, and `CConj`.
- Introduce an explicit immutable matching context that replaces Matchete globals: field degrees of freedom, heavy/light type classes, inferred masses, gauge couplings, fluctuation operators, X-term EFT/order metadata, and trace inventory.
- Extend functional derivatives to support second variational derivatives with ordered open differential operators:
  - subtract kinetic/free propagator terms before X-term extraction;
  - preserve open `CD`s in `FuncNCM`;
  - decompose X-terms by EFT order, loop-momentum power, and remaining open-CD count.
- Implement generic supertrace construction:
  - Matchete-style field-type trace enumeration with cyclic de-duplication;
  - bosonic/fermionic hard-region propagator expansions;
  - log-type traces for charged heavy fields;
  - power-type traces for the VLF trace list.
- Implement trace evaluation:
  - substitute X/M/gauge/Wilson insertions;
  - commute open CDs rightward and act on Wilson lines;
  - close fermion loops using the hybrid spinor basis;
  - carry out Dirac traces/refinement through idenso where applicable, with existing Symbolica fallbacks only where needed.
- Implement loop integration:
  - internal `LFFull` represents the full tadpole integral;
  - user-facing `LF` represents only the finite part;
  - provide `evaluate_loop_functions(...)` to expand finite `LF`s to poles/logs when comparing with Matchete-style evaluated output.
- Public API:
  - keep `Theory.match(..., loop_order=0)` unchanged;
  - add `loop_order=1` for tree plus one-loop off-shell matching;
  - add `loop_order=(1,)` or an equivalent function for one-loop-only output;
  - add a low-level `covariant_loop(...)`/trace API for individual VLF supertrace validation.

## Validation Plan

- Unit-test new symbols, printing, serialization, and public API docstring exports.
- Add functional-operator tests for scalar and fermion second derivatives, including open-CD ordering.
- Add VLF context tests for field dofs, X-order minima, X-term samples, mass substitutions, gauge substitutions, and exact trace inventory.
- Add propagator/log expansion tests at low orders against Matchete formulas.
- Add Wilson-line derivative tests for U(1) coincidence-limit terms through the orders needed by VLF dimension 6.
- Port relevant `LoopIntegration.wl` tests for `LFFull`, `LF`, pole separation, and finite evaluation.
- Add individual VLF supertrace tests and one full off-shell dimension-6 test, using pychete-native expected expressions derived from Matchete outputs; tests must not depend on reading executable Matchete source at runtime.
- Verify with:
  `source "$HOME/.bashrc" && dependencies/.venv/bin/python -m pytest tests`

## Assumptions

- Scope is full off-shell VLF dimension-6 one-loop output; on-shell EOM reduction, basis simplification, Greens simplification, counterterms, dimensional reduction, evanescent-only traces, ghosts, and heavy vectors are out of this slice.
- The default internal/user result keeps explicit poles plus finite `LF` placeholders; evaluated logs are available through `evaluate_loop_functions`.
- The public pychete model remains field/bar oriented, while internal fermion trace validation may use Matchete-compatible charge-conjugate spinor objects.
- General Lie-group abstractions remain group-agnostic; U(1) is fully supported for VLF, and non-Abelian/color-specific shortcuts are not introduced.

## Notebook Follow-Up

Add the one-loop matching to the VLF section of the jupyter example notebook.

## Loop-Function Convention Clarification

I don't like this. We should have exactly the LF's of Matchete, specified exclusively by and a tuple of integers and a tuple of masses.

Stop! Don't try to reverse engineer the log. Determine what loop function gave the log in the first place, and keep that as an LF.

Matchete's default evaluation of single-mass LFs is good. Keep using that, but then write the result with those logs. Understood?

## LaTeX Gamma Follow-Up

We need to add Latex output for Gamma with multiple indices.
