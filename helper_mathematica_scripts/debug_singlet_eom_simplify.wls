#!/usr/bin/env wolframscript
(* ::Package:: *)

(* Development-only Matchete EOMSimplify frontier dump for the Singlet scalar
   extension. Runtime pychete code and pytest must not depend on this script.

   Usage:
     wolframscript -file helper_mathematica_scripts/debug_singlet_eom_simplify.wls \
       --out assets/validation/matchete/debug/singlet_eom_cHD.debug.json
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

absolutePathQ[path_String] := StringStartsQ[path, $PathnameSeparator] ||
  StringMatchQ[path, LetterCharacter ~~ ":" ~~ ___];

outFileOption = optionValue[
  "out",
  FileNameJoin[{"assets", "validation", "matchete", "debug", "singlet_eom_cHD.debug.json"}]
];
outFile = If[absolutePathQ[outFileOption], outFileOption, FileNameJoin[{repoRoot, outFileOption}]];
targetOption = optionValue["target", "cHD"];
sampleChars = ToExpression @ optionValue["sample-chars", "2500"];

If[!DirectoryQ[matcheteRoot],
  Print["Matchete checkout not found: ", matcheteRoot];
  Quit[2];
];
If[!DirectoryQ[DirectoryName[outFile]],
  CreateDirectory[DirectoryName[outFile], CreateIntermediateDirectories -> True]
];

SetDirectory[matcheteRoot];
Get["Kernel/init.m"];
Matchete`LoadModel["SMEFT_Warsaw"];

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

stageSummary[name_String, expr_] := Module[{terms = termList[expr]},
  <|
    "name" -> name,
    "byte_count" -> ByteCount[expr],
    "term_count" -> Length[terms],
    "sample_terms_input_form" -> (shortInputString /@ Take[terms, UpTo[3]])
  |>
];

fieldsToShiftPreparation[expr_] := Module[{fields, freeL, list, shiftFields, prepared},
  fields = DeleteDuplicates @ Cases[expr, HoldPattern @ Matchete`Field[a_, __] :> a, Infinity];
  freeL = Matchete`PackageScope`InternalSimplify @ Total[Matchete`FreeLag[#] & /@ fields];
  prepared = Collect[expr - freeL, _Matchete`PackageScope`Operator];
  prepared = prepared - Matchete`SelectOperatorClass[prepared, {}, 4];
  list = Cases[
    Matchete`PackageScope`TermsToList @ prepared,
    x_ /; MemberQ[x, Matchete`PackageScope`EoM[___], {0, Infinity}]
  ];
  shiftFields = DeleteDuplicates @ Cases[
    list,
    Matchete`PackageScope`EoM[Matchete`Field[f_, ___]] |
      Matchete`PackageScope`EoM[Matchete`Bar @ Matchete`Field[f_, ___]] |
      Matchete`PackageScope`EoM[Matchete`Transp @ Matchete`Field[f_, ___]] :> f,
    Infinity
  ];
  <|
    "input_field_labels_input_form" -> toInputString[fields],
    "eom_term_count" -> Length[list],
    "eom_field_labels_input_form" -> toInputString[shiftFields],
    "sample_eom_terms_input_form" -> (shortInputString /@ Take[list, UpTo[5]])
  |>
];

higgsScalarShiftSummary[expr_] := Module[
  {fields, hField, real, type, freeL, prepared, hTerms, hEomTerms, rules},
  fields = DeleteDuplicates @ Cases[expr, HoldPattern @ Matchete`Field[a_, __] :> a, Infinity];
  hField = FirstCase[fields, f_ /; SymbolName[Unevaluated[f]] === "H", Missing["NotFound"]];
  If[hField === Missing["NotFound"], Return[<|"available" -> False|>]];
  {real, type} = Lookup[Matchete`PackageScope`$FieldAssociation @ hField, {Matchete`SelfConjugate, Matchete`Type}];
  freeL = Matchete`PackageScope`InternalSimplify @ Total[Matchete`FreeLag[#] & /@ fields];
  prepared = Collect[expr - freeL, _Matchete`PackageScope`Operator];
  prepared = prepared - Matchete`SelectOperatorClass[prepared, {}, 4];
  hTerms = Select[Matchete`PackageScope`TermsToList @ prepared, Not @* FreeQ[hField]];
  hEomTerms = Select[hTerms, MemberQ[#, Matchete`PackageScope`EoM[___], {0, Infinity}] &];
  rules = If[
    hEomTerms === {},
    {},
    Matchete`FieldRedef`PackagePrivate`ScalarShift[Plus @@ hEomTerms, hField, real]
  ];
  <|
    "available" -> True,
    "field_type_input_form" -> toInputString[type],
    "self_conjugate" -> TrueQ[real],
    "terms_containing_h_count" -> Length[hTerms],
    "eom_terms_containing_h_count" -> Length[hEomTerms],
    "sample_h_eom_terms_input_form" -> (shortInputString /@ Take[hEomTerms, UpTo[3]]),
    "rules_input_form" -> shortInputString[rules]
  |>
];

operatorForTarget["cHD"] := Module[{i = Unique["i"], j = Unique["j"], nu = Unique["nu"]},
  H[i] Matchete`CD[nu, Matchete`Bar[H[i]]] Matchete`Bar[H[j]] Matchete`CD[nu, H[j]]
];
operatorForTarget[other_] := (
  Print["Unsupported target for this EOMSimplify dump: ", other];
  Quit[2]
);

previousValidationFile = FileNameJoin[{
  matcheteRoot,
  "Validation",
  "MatchingResults",
  "previous",
  "Singlet_Scalar_Extension-EFT.m"
}];
If[!FileExistsQ[previousValidationFile],
  Print["Previous validation result not found: ", previousValidationFile];
  Quit[2]
];

previousValidationResult = Get[previousValidationFile];
offShell = previousValidationResult["Off-shell EFT Lagrangian"];
onShell = previousValidationResult["On-shell EFT Lagrangian"];
operator = operatorForTarget[targetOption];
fieldsToShift = Matchete`PackageScope`FieldsToShift[offShell];
fieldsToShiftPrep = fieldsToShiftPreparation[offShell];
higgsShift = higgsScalarShiftSummary[offShell];

offCoefficient = Matchete`GetOperatorCoefficient[offShell, operator];
onCoefficient = Matchete`GetOperatorCoefficient[onShell, operator];
deltaCoefficient = FullSimplify[onCoefficient - offCoefficient];

data = <|
  "schema_version" -> 1,
  "generator" -> "debug_singlet_eom_simplify.wls",
  "model" -> "Singlet_Scalar_Extension",
  "target" -> targetOption,
  "previous_validation_file" -> previousValidationFile,
  "operator_input_form" -> toInputString[operator],
  "off_shell_coefficient_input_form" -> toInputString[offCoefficient],
  "on_shell_coefficient_input_form" -> toInputString[onCoefficient],
  "on_minus_off_coefficient_input_form" -> toInputString[deltaCoefficient],
  "fields_to_shift_input_form" -> toInputString[fieldsToShift],
  "fields_to_shift_preparation" -> fieldsToShiftPrep,
  "higgs_scalar_shift_summary" -> higgsShift,
  "off_shell_summary" -> stageSummary["off_shell_eft_lagrangian", offShell],
  "on_shell_summary" -> stageSummary["on_shell_eft_lagrangian", onShell],
  "on_minus_off_summary" -> stageSummary["on_minus_off_eft_lagrangian", onShell - offShell]
|>;

Export[outFile, data, "RawJSON"];
Print["Wrote ", outFile];
Quit[0];
