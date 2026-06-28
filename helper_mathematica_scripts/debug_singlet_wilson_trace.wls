#!/usr/bin/env wolframscript
(* ::Package:: *)

(* Development-only Matchete intermediate-stage dump for the Singlet scalar
   extension hScalar-lScalar Wilson-line/power-trace frontier.

   Usage:
     wolframscript -file helper_mathematica_scripts/debug_singlet_wilson_trace.wls \
       --out assets/validation/matchete/debug/singlet_hScalar_lScalar_cHW.debug.json

   Runtime pychete code and pytest must never depend on this script. It exists
   so pychete development can compare Matchete's own intermediate supertrace
   stages against pychete's Wilson-line diagnostics when chasing parity gaps.
*)

args = Rest @ $ScriptCommandLine;

optionValue[name_String, default_String] := Module[{pos},
  pos = FirstPosition[args, "--" <> name, Missing["NotFound"], {1}, Heads -> False];
  If[pos === Missing["NotFound"] || Length[args] < pos[[1]] + 1,
    default,
    args[[pos[[1]] + 1]]
  ]
];

repoRoot = DirectoryName[DirectoryName[$InputFileName]];
matcheteRoot = FileNameJoin[{repoRoot, "mathematica_reference", "Matchete"}];
If[!DirectoryQ[matcheteRoot],
  matcheteRoot = FileNameJoin[{repoRoot, "Mathematica_reference", "Matchete"}]
];

outFileOption = optionValue[
  "out",
  FileNameJoin[{
    "assets",
    "validation",
    "matchete",
    "debug",
    "singlet_hScalar_lScalar_cHW.debug.json"
  }]
];
absolutePathQ[path_String] := StringStartsQ[path, $PathnameSeparator] ||
  StringMatchQ[path, LetterCharacter ~~ ":" ~~ ___];

outFile = If[!absolutePathQ[outFileOption],
  FileNameJoin[{repoRoot, outFileOption}],
  outFileOption
];
propOrderOption = ToExpression @ optionValue["prop-order", "4"];
sampleChars = ToExpression @ optionValue["sample-chars", "2500"];
sampleTerms = ToExpression @ optionValue["sample-terms", "3"];
targetOption = ToExpression @ optionValue["target", "cHW"];

If[!DirectoryQ[matcheteRoot],
  Print["Matchete checkout not found: ", matcheteRoot];
  Quit[2];
];

If[!DirectoryQ[DirectoryName[outFile]],
  CreateDirectory[DirectoryName[outFile], CreateIntermediateDirectories -> True]
];

SetDirectory[matcheteRoot];
Get["Kernel/init.m"];

toInputString[expr_] := ToString[Unevaluated[expr], InputForm, CharacterEncoding -> "PrintableASCII"];

shortInputString[expr_] := Module[{s = toInputString[expr]},
  If[StringLength[s] > sampleChars, StringTake[s, sampleChars] <> "...", s]
];

termList[expr_] := Module[{expanded = Expand[expr]},
  Which[
    expanded === 0, {},
    Head[expanded] === Plus, List @@ expanded,
    True, {expanded}
  ]
];

termSignature[term_] := {
  Length @ Cases[term, Matchete`Field[H, Matchete`Scalar, __], All],
  Length @ Cases[term, Matchete`Bar[Matchete`Field[H, Matchete`Scalar, __]], All],
  Length @ Cases[term, Matchete`Field[\[Phi], Matchete`Scalar, __], All],
  Length @ Cases[term, Matchete`FieldStrength[W, __], All],
  Length @ Cases[term, Matchete`PackageScope`WilsonTerm[__], All],
  Length @ Cases[term, Matchete`PackageScope`OpenCD[__], All],
  Length @ Cases[term, Matchete`PackageScope`LoopMom[__], All],
  Length @ Cases[term, Matchete`PackageScope`Prop[__], All],
  Length @ Cases[term, Matchete`SuperTrace`PackagePrivate`FSWilsonFactor[__], All]
};

signatureHistogram[terms_List] := Module[{counts},
  counts = Normal @ Counts[termSignature /@ terms];
  (Function[row,
    <|
      "h_atoms" -> row[[1, 1]],
      "bar_h_atoms" -> row[[1, 2]],
      "phi_atoms" -> row[[1, 3]],
      "w_field_strength_atoms" -> row[[1, 4]],
      "wilson_terms" -> row[[1, 5]],
      "open_cds" -> row[[1, 6]],
      "loop_momenta" -> row[[1, 7]],
      "propagators" -> row[[1, 8]],
      "fs_wilson_factors" -> row[[1, 9]],
      "count" -> row[[2]]
    |>
  ] /@ counts)
];

derivativeWord[inds_List] := Module[{keys = {}, word = {}, key, pos},
  If[Length[inds] == 0, Return["0"]];
  Do[
    key = toInputString[ind];
    pos = FirstPosition[keys, key, Missing["NotFound"], {1}, Heads -> False];
    If[pos === Missing["NotFound"],
      AppendTo[keys, key];
      AppendTo[word, FromCharacterCode[96 + Length[keys]]],
      AppendTo[word, FromCharacterCode[96 + pos[[1]]]]
    ],
    {ind, inds}
  ];
  StringJoin[word]
];

barHDerivativeWords[term_] := derivativeWord /@ Cases[
  term,
  Matchete`Bar[Matchete`Field[H, Matchete`Scalar, _, derivs_]] :> derivs,
  All
];

hDerivativeWords[term_] := Module[{withoutBars},
  withoutBars = DeleteCases[
    term,
    Matchete`Bar[Matchete`Field[H, Matchete`Scalar, _, _]],
    All
  ];
  derivativeWord /@ Cases[
    withoutBars,
    Matchete`Field[H, Matchete`Scalar, _, derivs_] :> derivs,
    All
  ]
];

termDerivativeSignature[term_] := Module[{barWords, hWords},
  barWords = barHDerivativeWords[term];
  hWords = hDerivativeWords[term];
  "bar=" <> If[Length[barWords] == 0, "none", StringRiffle[barWords, ","]] <>
    ";field=" <> If[Length[hWords] == 0, "none", StringRiffle[hWords, ","]]
];

derivativeWordHistogram[terms_List] := Module[{counts},
  counts = Normal @ Counts[termDerivativeSignature /@ terms];
  (Function[row,
    <|
      "signature" -> row[[1]],
      "count" -> row[[2]]
    |>
  ] /@ counts)
];

derivativeSignatureSamples[terms_List] := Module[{samples = <||>, sig},
  Do[
    sig = termDerivativeSignature[term];
    If[!KeyExistsQ[samples, sig],
      samples[sig] = shortInputString[term]
    ],
    {term, terms}
  ];
  KeyValueMap[
    Function[{signature, sample},
      <|
        "signature" -> signature,
        "sample_input_form" -> sample
      |>
    ],
    samples
  ]
];

hBilinearFactors[term_] := Module[{barAtoms, withoutBars, hAtoms},
  barAtoms = Cases[
    term,
    Matchete`Bar[Matchete`Field[H, Matchete`Scalar, _, _]],
    All
  ];
  withoutBars = DeleteCases[
    term,
    Matchete`Bar[Matchete`Field[H, Matchete`Scalar, _, _]],
    All
  ];
  hAtoms = Cases[
    withoutBars,
    Matchete`Field[H, Matchete`Scalar, _, _],
    All
  ];
  {barAtoms, hAtoms}
];

hBilinearCoefficientSlices[expr_] := Module[
  {rows = <||>, barAtoms, hAtoms, sig, coeff},
  If[expr === $Aborted || expr === $Failed, Return[{}]];
  Do[
    {barAtoms, hAtoms} = hBilinearFactors[term];
    If[Length[barAtoms] =!= 1 || Length[hAtoms] =!= 1, Continue[]];
    sig = termDerivativeSignature[term];
    coeff = Together[term/(Times @@ barAtoms * Times @@ hAtoms)];
    rows[sig] = Together[Lookup[rows, sig, 0] + coeff],
    {term, termList[expr]}
  ];
  KeyValueMap[
    Function[{signature, coefficient},
      <|
        "signature" -> signature,
        "coefficient_input_form" -> toInputString[coefficient],
        "coefficient_sample_input_form" -> shortInputString[coefficient]
      |>
    ],
    KeySort[rows]
  ]
];

symGammaHistogram[terms_List] := Module[{counts},
  counts = Normal @ Counts[
    Cases[
      #,
      Matchete`PackageScope`SymGammaFactor[n_, d_] :> {n, d},
      All
    ] & /@ terms
  ];
  (Function[row,
    <|
      "factors_input_form" -> toInputString[row[[1]]],
      "count" -> row[[2]]
    |>
  ] /@ counts)
];

fsWilsonFactorDerivativeHistogram[terms_List] := Module[{counts},
  counts = Normal @ Counts[
    {termDerivativeSignature[#],
      Length @ Cases[#, Matchete`SuperTrace`PackagePrivate`FSWilsonFactor[__], All] > 0} & /@ terms
  ];
  (Function[row,
    <|
      "signature" -> row[[1, 1]],
      "has_fs_wilson_factor" -> row[[1, 2]],
      "count" -> row[[2]]
    |>
  ] /@ counts)
];

noFSWilsonFactorExpression[expr_] := Module[{selected},
  If[expr === $Aborted || expr === $Failed, Return[expr]];
  selected = Select[
    termList[expr],
    FreeQ[#, Matchete`SuperTrace`PackagePrivate`FSWilsonFactor[__], All] &
  ];
  If[Length[selected] == 0, 0, Total[selected]]
];

withFSWilsonFactorExpression[expr_] := Module[{selected},
  If[expr === $Aborted || expr === $Failed, Return[expr]];
  selected = Select[
    termList[expr],
    ! FreeQ[#, Matchete`SuperTrace`PackagePrivate`FSWilsonFactor[__], All] &
  ];
  If[Length[selected] == 0, 0, Total[selected]]
];

stageSummary[name_String, expr_] := Module[{terms = termList[expr]},
  If[expr === $Aborted || expr === $Failed,
    Return @ <|
      "name" -> name,
      "aborted_or_failed" -> True,
      "input_form" -> toInputString[expr],
      "byte_count" -> ByteCount[expr],
      "term_count" -> 0,
      "h_atoms" -> 0,
      "bar_h_atoms" -> 0,
      "phi_atoms" -> 0,
      "w_field_strength_atoms" -> 0,
      "wilson_terms" -> 0,
      "open_cds" -> 0,
      "loop_momenta" -> 0,
      "propagators" -> 0,
      "fs_wilson_factors" -> 0,
      "sym_gamma_factors" -> 0,
      "signature_histogram" -> {},
      "h_derivative_word_histogram" -> {},
      "h_derivative_signature_samples" -> {},
      "sym_gamma_histogram" -> {},
      "fs_wilson_factor_derivative_histogram" -> {},
      "sample_terms_input_form" -> {}
    |>
  ];
  <|
    "name" -> name,
    "byte_count" -> ByteCount[expr],
    "term_count" -> Length[terms],
    "h_atoms" -> Length @ Cases[expr, Matchete`Field[H, Matchete`Scalar, __], All],
    "bar_h_atoms" -> Length @ Cases[expr, Matchete`Bar[Matchete`Field[H, Matchete`Scalar, __]], All],
    "phi_atoms" -> Length @ Cases[expr, Matchete`Field[\[Phi], Matchete`Scalar, __], All],
    "w_field_strength_atoms" -> Length @ Cases[expr, Matchete`FieldStrength[W, __], All],
    "wilson_terms" -> Length @ Cases[expr, Matchete`PackageScope`WilsonTerm[__], All],
    "open_cds" -> Length @ Cases[expr, Matchete`PackageScope`OpenCD[__], All],
    "loop_momenta" -> Length @ Cases[expr, Matchete`PackageScope`LoopMom[__], All],
    "propagators" -> Length @ Cases[expr, Matchete`PackageScope`Prop[__], All],
    "fs_wilson_factors" -> Length @ Cases[
      expr,
      Matchete`SuperTrace`PackagePrivate`FSWilsonFactor[__],
      All
    ],
    "sym_gamma_factors" -> Length @ Cases[expr, Matchete`PackageScope`SymGammaFactor[__], All],
    "signature_histogram" -> signatureHistogram[terms],
    "h_derivative_word_histogram" -> derivativeWordHistogram[terms],
    "h_derivative_signature_samples" -> derivativeSignatureSamples[terms],
    "sym_gamma_histogram" -> symGammaHistogram[terms],
    "fs_wilson_factor_derivative_histogram" -> fsWilsonFactorDerivativeHistogram[terms],
    "sample_terms_input_form" -> (shortInputString /@ Take[terms, UpTo[sampleTerms]])
  |>
];

SetAttributes[safeEvaluate, HoldFirst];
safeEvaluate[expr_] := CheckAbort[Quiet[Check[expr, $Failed]], $Aborted];

failedEvaluationQ[expr_] := expr === $Aborted || expr === $Failed;

validationTraceStages[expr_] := Module[
  {
    contracted,
    reduced,
    simplified
  },
  contracted = safeEvaluate @ Matchete`ContractCGs[expr];
  reduced = If[failedEvaluationQ[contracted],
    contracted,
    safeEvaluate @ Matchete`PackageScope`MatchReduce[contracted]
  ];
  simplified = If[failedEvaluationQ[reduced],
    reduced,
    safeEvaluate @ Matchete`GreensSimplify[reduced]
  ];

  <|
    "result" -> simplified,
    "stages" -> {
      stageSummary["validation_input", expr],
      stageSummary["validation_contract_cgs", contracted],
      stageSummary["validation_match_reduce", reduced],
      stageSummary["validation_greens_simplify", simplified]
    }
  |>
];

validationTraceSimplify[expr_] := validationTraceStages[expr]["result"];

Begin["Matchete`SuperTrace`PackagePrivate`"];
GenericPropagatorExpansionForOrderTuple[propTypes_List, orders_List] := Module[
    {gaugeCouplings, genInds, n, masses, props, Xops, types, propNo = Length @ propTypes},
  genInds = Table[Symbol["$i" <> ToString @ n], {n, propNo + 1}];
  Xops = MapThread[Matchete`PackageScope`Xop,
    {Partition[propTypes, 2, 1, 1], Partition[genInds, 2, 1], Table[n, {n, propNo}]}];
  AppendTo[Xops, Matchete`PackageScope`WilsonLine[First @ propTypes, genInds[[{-1, 1}]]]];
  types = RotateLeft[propTypes];
  masses = MapThread[Matchete`PackageScope`Mop, {types, genInds[[2 ;;]], Table[n, {n, propNo}]}];
  gaugeCouplings = Times @@ Table[
    If[types[[n]] === Matchete`PackageScope`lVector, Matchete`PackageScope`GaugeCop[n], 1],
    {n, propNo}
  ];
  props = MapThread[PropAtOrder, {types, masses, orders}];
  gaugeCouplings * Matchete`PackageScope`FuncNCM @@ (Riffle[Xops, props] /. PropAtOrder -> PropExpand) // Expand
];
End[];

evaluateEarlyStages[gen_, insertion_] := Module[
  {
    factor = insertion[[1]],
    replacement = insertion[[2]],
    substituted,
    acted,
    gathered,
    removed
  },

  substituted = factor gen /. replacement /. Matchete`PackageScope`$Xsubs /.
    Matchete`PackageScope`$Msubs /. Matchete`PackageScope`$Gsubs;
  acted = Matchete`PackageScope`ActWithOpenCDs[substituted] /.
    Matchete`PackageScope`FuncNCM -> Matchete`NCM;
  gathered = Matchete`PackageScope`GatherLoopMomenta[acted];
  removed = Matchete`PackageScope`RemoveSymmetryVanishingWilsonTerms[gathered];

  <|
    "factor_input_form" -> toInputString[factor],
    "replacement_input_form" -> toInputString[replacement],
    "stages" -> {
      stageSummary["slot_substituted", substituted],
      stageSummary["slot_acted_open_cds", acted],
      stageSummary["slot_gathered_loop_momenta", gathered],
      stageSummary["slot_removed_symmetry_vanishing_wilson_terms", removed]
    }
  |>
];

orderTupleStageSummaries[propTypes_, propOrder_, insertions_] := Module[
  {orderTuples, tupleGen},
  orderTuples = Matchete`PackageScope`IntegerSets[propOrder, Length @ propTypes];
  Map[
    Function[orders,
      tupleGen = Matchete`SuperTrace`PackagePrivate`GenericPropagatorExpansionForOrderTuple[
        propTypes,
        orders
      ];
      <|
        "slot_orders" -> orders,
        "generator_summary" -> stageSummary[
          "generic_propagator_expansion_slot_" <> toInputString[orders],
          tupleGen
        ],
        "insertions" -> MapIndexed[
          Join[
            <|"index" -> First[#2]|>,
            evaluateEarlyStages[tupleGen, #1]
          ] &,
          insertions
        ]
      |>
    ],
    orderTuples
  ]
];

evaluateStages[gen_, insertion_, propTypes_] := Module[
  {
    factor = insertion[[1]],
    replacement = insertion[[2]],
    substituted,
    acted,
    gathered,
    removed,
    closed,
    symmetric,
    metric,
    wilson,
    integrated,
    wilsonNoFS,
    integratedNoFS,
    integratedWithFS,
    post,
    postNoFS,
    eps,
    evaluated,
    validationSimplification,
    validationSimplified
  },

  substituted = factor gen /. replacement /. Matchete`PackageScope`$Xsubs /.
    Matchete`PackageScope`$Msubs /. Matchete`PackageScope`$Gsubs;
  acted = Matchete`PackageScope`ActWithOpenCDs[substituted] /.
    Matchete`PackageScope`FuncNCM -> Matchete`NCM;
  gathered = Matchete`PackageScope`GatherLoopMomenta[acted];
  removed = Matchete`PackageScope`RemoveSymmetryVanishingWilsonTerms[gathered];
  closed = Matchete`PackageScope`CloseFermionLoop[removed, propTypes];
  symmetric = Matchete`PackageScope`EvaluateSymmetricLorentzInds[closed];
  metric = Matchete`PackageScope`ContractMetric[symmetric];
  wilson = Matchete`PackageScope`WilsonExpand[metric];
  integrated = Matchete`PackageScope`LoopIntegrate[wilson];
  wilsonNoFS = noFSWilsonFactorExpression[wilson];
  integratedNoFS = noFSWilsonFactorExpression[integrated];
  integratedWithFS = withFSWilsonFactorExpression[integrated];
  post = safeEvaluate @ Matchete`RefineDiracProducts[
    Matchete`PackageScope`ContractDelta[
      Matchete`ContractCGs[
        Matchete`PackageScope`ContractDelta[
          Matchete`PackageScope`ExpandGenFSs[
            Matchete`RelabelIndices[integrated]
          ]
        ]
      ]
    ]
  ];
  postNoFS = noFSWilsonFactorExpression[post];
  eps = If[post === $Aborted || post === $Failed,
    post,
    safeEvaluate @ Matchete`RelabelIndices[Matchete`PackageScope`EpsExpand[post]]
  ];
  evaluated = safeEvaluate @ Matchete`PackageScope`EvaluateSTr[
    gen,
    insertion,
    propTypes,
    Matchete`Matching
  ];
  validationSimplification = validationTraceStages[preFactor evaluated];
  validationSimplified = validationSimplification["result"];

  <|
    "factor_input_form" -> toInputString[factor],
    "replacement_input_form" -> toInputString[replacement],
    "stages" -> {
      stageSummary["substituted", substituted],
      stageSummary["acted_open_cds", acted],
      stageSummary["gathered_loop_momenta", gathered],
      stageSummary["removed_symmetry_vanishing_wilson_terms", removed],
      stageSummary["closed_fermion_loop", closed],
      stageSummary["evaluated_symmetric_lorentz_indices", symmetric],
      stageSummary["contracted_metric", metric],
      stageSummary["wilson_expanded", wilson],
      stageSummary["loop_integrated", integrated],
      stageSummary["wilson_expanded_no_fs_wilson_factor", wilsonNoFS],
      stageSummary["loop_integrated_no_fs_wilson_factor", integratedNoFS],
      stageSummary["loop_integrated_with_fs_wilson_factor", integratedWithFS],
      stageSummary["post_index_group_cleanup", post],
      stageSummary["post_index_group_cleanup_no_fs_wilson_factor", postNoFS],
      stageSummary["eps_expanded_relabelled", eps],
      stageSummary["evaluate_str_reference", evaluated],
      stageSummary["validation_simplified_prefactored_evaluate_str", validationSimplified]
    },
    "wilson_expanded_no_fs_wilson_factor_input_form" -> shortInputString[wilsonNoFS],
	    "loop_integrated_no_fs_wilson_factor_input_form" -> shortInputString[integratedNoFS],
	    "loop_integrated_with_fs_wilson_factor_input_form" -> shortInputString[integratedWithFS],
	    "post_index_group_cleanup_no_fs_wilson_factor_input_form" -> shortInputString[postNoFS],
	    "loop_integrated_no_fs_wilson_factor_h_bilinear_coefficients" ->
	      hBilinearCoefficientSlices[integratedNoFS],
	    "post_index_group_cleanup_no_fs_wilson_factor_h_bilinear_coefficients" ->
	      hBilinearCoefficientSlices[postNoFS],
	    "eps_expanded_relabelled_h_bilinear_coefficients" ->
	      hBilinearCoefficientSlices[eps],
	    "prefactored_eps_expanded_relabelled_h_bilinear_coefficients" ->
	      hBilinearCoefficientSlices[preFactor eps],
	    "evaluate_str_reference_h_bilinear_coefficients" ->
	      hBilinearCoefficientSlices[evaluated],
	    "prefactored_evaluate_str_reference_h_bilinear_coefficients" ->
	      hBilinearCoefficientSlices[preFactor evaluated],
	    "validation_simplification_stage_summaries" -> validationSimplification["stages"],
	    "validation_simplified_prefactored_evaluate_str_input_form" ->
	      shortInputString[validationSimplified],
    "manual_minus_evaluate_str_input_form" -> If[
      eps === $Aborted || eps === $Failed || evaluated === $Aborted || evaluated === $Failed,
      toInputString[{eps, evaluated}],
      shortInputString[eps - evaluated]
    ]
  |>
];

ResetAll[];
Matchete`PackageScope`ActivateValidationMode["Singlet_Scalar_Extension", False];
Begin["Global`"];
luv = LoadModel["Singlet_Scalar_Extension"];
End[];

lag = Matchete`PackageScope`SetCurrentLagrangian[luv, 1, 6, System`Verbose -> False];
propTypes = {Matchete`PackageScope`hScalar, Matchete`PackageScope`lScalar};
propOrder = propOrderOption;
gen = Matchete`SuperTrace`PackagePrivate`GenericPropagatorExpansion[propTypes, propOrder];
insertions = Matchete`SuperTrace`PackagePrivate`DeterminePowerInsertions[
  propTypes,
  6 - propOrder,
  All
];
preFactor = -I hbar/2;
rawInsertionSum = safeEvaluate @ Total[
  Matchete`PackageScope`EvaluateSTr[gen, #, propTypes, Matchete`Matching] & /@ insertions
];
powerTypeTrace = safeEvaluate @ Matchete`PackageScope`PowerTypeSTr[propTypes, 6];
selectedPropOrderValidationStages = validationTraceStages[preFactor rawInsertionSum];
selectedPropOrderValidationSimplified = selectedPropOrderValidationStages["result"];
fullTraceValidationStages = validationTraceStages[powerTypeTrace];
fullTraceValidationSimplified = fullTraceValidationStages["result"];
previousValidationFile = FileNameJoin[{
  matcheteRoot,
  "Validation",
  "MatchingResults",
  "previous",
  "Singlet_Scalar_Extension-EFT.m"
}];
previousValidationResult = If[FileExistsQ[previousValidationFile],
  Get[previousValidationFile],
  <||>
];
previousValidationTrace = If[AssociationQ[previousValidationResult],
  previousValidationResult["SuperTraces"]["hScalar-lScalar"],
  $Failed
];
previousTargetCondition = If[AssociationQ[previousValidationResult],
  Cases[
    previousValidationResult["Matching Conditions"],
    Rule[Matchete`Coupling[targetOption, {}, 0], rhs_] :> rhs,
    All
  ],
  {}
];
selectedXTermValues = safeEvaluate @ {
  Matchete`PackageScope`Xterm[{\[Phi], H}, {i, j}, 1, 0, 0],
  Matchete`PackageScope`Xterm[{H, \[Phi]}, {i, j}, 1, 0, 0],
  Matchete`PackageScope`Xterm[{\[Phi], Matchete`PackageScope`Conj[H]}, {i, j}, 1, 0, 0],
  Matchete`PackageScope`Xterm[{Matchete`PackageScope`Conj[H], \[Phi]}, {i, j}, 1, 0, 0]
} /. Matchete`PackageScope`$Xsubs;

data = <|
  "schema_version" -> 1,
  "generator" -> "debug_singlet_wilson_trace.wls",
  "model" -> "Singlet_Scalar_Extension",
  "trace_name" -> "hScalar-lScalar",
  "target" -> toInputString[targetOption],
  "prop_order" -> propOrder,
  "eft_order" -> 6,
  "matchete_root" -> matcheteRoot,
  "x_field_dofs_input_form" -> toInputString[Matchete`PackageScope`$XFieldDofs],
  "selected_x_orders_input_form" -> toInputString[
    KeyTake[
      Matchete`PackageScope`$XOrders,
      {{\[Phi], H}, {H, \[Phi]}, {\[Phi], Conj[H]}, {Conj[H], \[Phi]}}
    ]
  ],
  "selected_xterm_values_input_form" -> toInputString[selectedXTermValues],
  "propagator_expansion_summary" -> stageSummary["generic_propagator_expansion", gen],
  "slot_order_stage_summaries" -> orderTupleStageSummaries[propTypes, propOrder, insertions],
  "insertion_count" -> Length[insertions],
  "insertions" -> MapIndexed[
    Join[
      <|"index" -> First[#2]|>,
      evaluateStages[gen, #1, propTypes]
    ] &,
    insertions
  ],
  "raw_insertion_sum_summary" -> stageSummary["raw_insertion_sum_no_power_prefactor", rawInsertionSum],
  "power_prefactor_input_form" -> toInputString[preFactor],
  "power_prefactor_times_raw_sum_summary" -> stageSummary[
    "power_prefactor_times_raw_sum",
    preFactor rawInsertionSum
  ],
  "selected_prop_order_validation_simplified_summary" -> stageSummary[
    "selected_prop_order_validation_simplified",
    selectedPropOrderValidationSimplified
  ],
  "selected_prop_order_validation_stage_summaries" ->
    selectedPropOrderValidationStages["stages"],
  "selected_prop_order_validation_simplified_input_form" ->
    shortInputString[selectedPropOrderValidationSimplified],
  "full_power_type_trace_summary" -> stageSummary[
    "full_power_type_trace_all_prop_orders",
    powerTypeTrace
  ],
  "full_trace_validation_simplified_summary" -> stageSummary[
    "full_trace_validation_simplified",
    fullTraceValidationSimplified
  ],
  "full_trace_validation_stage_summaries" ->
    fullTraceValidationStages["stages"],
  "previous_validation_file" -> previousValidationFile,
  "previous_validation_hScalar_lScalar_summary" -> stageSummary[
    "previous_validation_hScalar_lScalar",
    previousValidationTrace
  ],
  "previous_validation_target_condition_input_form" -> toInputString[previousTargetCondition],
  "previous_validation_cHW_condition_input_form" -> If[
    targetOption === cHW,
    toInputString[previousTargetCondition],
    "[]"
  ],
  "full_power_minus_selected_prop_order_input_form" -> shortInputString[
    powerTypeTrace - preFactor rawInsertionSum
  ]
|>;

Export[outFile, data, "RawJSON"];
Print["Wrote ", outFile];
Quit[0];
