#!/usr/bin/env wolframscript
(* ::Package:: *)

(* Development-only raw Matchete snapshot exporter.
   Usage:
     wolframscript -file helper_mathematica_scripts/export_matchete_matching_snapshots.wls \
       --out assets/validation/matchete/raw \
       --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs

   This script may load Matchete. Runtime pychete code and pytest must never
   depend on it. Its output is an intermediate development artifact that should
   be converted into pychete-owned fixtures before tests consume it.
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
matcheteRoot = FileNameJoin[{repoRoot, "Mathematica_reference", "Matchete"}];
outDir = optionValue["out", FileNameJoin[{repoRoot, "assets", "validation", "matchete", "raw"}]];
models = StringSplit[
  optionValue["models", "VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs"],
  ","
];

If[!DirectoryQ[matcheteRoot],
  Print["Matchete checkout not found: ", matcheteRoot];
  Quit[2];
];

If[!DirectoryQ[outDir], CreateDirectory[outDir, CreateIntermediateDirectories -> True]];

SetDirectory[matcheteRoot];
Block[{Print}, UsingFrontEnd @ Get["Kernel/init.m"]];

toInputString[expr_] := ToString[Unevaluated[expr], InputForm, CharacterEncoding -> "PrintableASCII"];

exportModel[model_String] := Module[
  {luv, matchResult, previousFile, previousResult, previousKeys, data, outFile},
  ResetAll[];
  Matchete`PackageScope`ActivateValidationMode[model, False];

  Begin["Global`"];
  luv = LoadModel[model];
  End[];

  matchResult = Match[luv, EFTOrder -> 6, LoopOrder -> 1];
  previousFile = FileNameJoin[{
    matcheteRoot,
    "Validation",
    "MatchingResults",
    "previous",
    model <> "-EFT.m"
  }];
  previousResult = If[FileExistsQ[previousFile], Get[previousFile], <||>];
  previousKeys = If[AssociationQ[previousResult], ToString /@ Keys[previousResult], {}];

  data = <|
    "schema_version" -> 1,
    "generator" -> "export_matchete_matching_snapshots.wls",
    "model" -> model,
    "matchete_root" -> matcheteRoot,
    "uv_lagrangian_input_form" -> toInputString[luv],
    "match_return_input_form" -> toInputString[matchResult],
    "previous_result_file" -> previousFile,
    "previous_result_keys" -> previousKeys,
    "previous_result_input_form" -> toInputString[previousResult]
  |>;

  outFile = FileNameJoin[{outDir, model <> ".raw.json"}];
  Export[outFile, data, "RawJSON"];
  Print["Wrote ", outFile];
];

Scan[exportModel, models];
Quit[0];
