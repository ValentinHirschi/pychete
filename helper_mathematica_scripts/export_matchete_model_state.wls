#!/usr/bin/env wolframscript
(* ::Package:: *)

(* Development-only Matchete loaded-model-state exporter.
   Usage:
     wolframscript -file helper_mathematica_scripts/export_matchete_model_state.wls \
       --out assets/validation/matchete/model_state \
       --models VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs

   This script may load Matchete and inspect Matchete's post-LoadModel
   metadata associations. Runtime pychete code and pytest must never depend on
   it. Convert this RawJSON output into pychete-owned fixtures with
   helper_mathematica_scripts/convert_matchete_model_state.py before committing
   validation assets.
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
outDir = optionValue["out", FileNameJoin[{repoRoot, "assets", "validation", "matchete", "model_state"}]];
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
toPlainString[expr_] := ToString[Unevaluated[expr], InputForm, CharacterEncoding -> "PrintableASCII"];
boolValue[expr_] := TrueQ[expr];
listInputStrings[expr_] := toInputString /@ Replace[expr, Except[_List] :> {expr}];

entryList[assoc_Association, mapper_] := KeyValueMap[mapper, assoc];

flavorEntry[label_, props_] := <|
  "name_input_form" -> toInputString[label],
  "dimension_input_form" -> toInputString[props[IndexDimension]]
|>;

groupEntry[kind_String][label_, props_] := <|
  "name_input_form" -> toInputString[label],
  "kind" -> kind,
  "group_input_form" -> toInputString[props[Group]],
  "coupling_input_form" -> If[KeyExistsQ[props, Coupling], toInputString[props[Coupling]], Null],
  "field_input_form" -> If[KeyExistsQ[props, Field], toInputString[props[Field]], Null],
  "abelian" -> boolValue[props[Abelian]]
|>;

representationEntry[label_, props_] := <|
  "name_input_form" -> toInputString[label],
  "group_input_form" -> toInputString[props[Group]],
  "dynkin_input_form" -> toInputString[props[DynkinCoefficients]],
  "dimension" -> props[Dimension],
  "reality_input_form" -> toInputString[props[Reality]]
|>;

cgEntry[label_] := Module[{tensor},
  tensor = Quiet[Check[GetCGTensor[label], $Failed]];
  <|
    "name_input_form" -> toInputString[label],
    "representations_input_form" -> listInputStrings[Matchete`PackageScope`$CGproperties[label, Indices]],
    "group_input_form" -> toInputString[Matchete`PackageScope`$CGproperties[label, Group]],
    "tensor_input_form" -> If[tensor === $Failed, Null, toInputString[tensor]]
  |>
];

couplingEntry[label_, props_] := <|
  "name_input_form" -> toInputString[label],
  "indices_input_form" -> listInputStrings[props[Indices]],
  "eft_order" -> props[EFTOrder],
  "mass_dimension" -> If[KeyExistsQ[props, MassDimension], props[MassDimension], Null],
  "self_conjugate_input_form" -> toInputString[props[SelfConjugate]],
  "symmetries_input_form" -> toInputString[props[Symmetries]],
  "diagonal_coupling" -> props[DiagonalCoupling],
  "thermal_power_counting" -> props[ThermalPowerCounting],
  "unitary" -> boolValue[props[Unitary]]
|>;

fieldRole[props_] := Which[
  boolValue[props[GoldstoneBoson]], "goldstone",
  boolValue[props[BackgroundField]], "background",
  props[Type] === Ghost, "ghost",
  props[Type] === AntiGhost, "anti_ghost",
  True, "physical"
];

fieldEntry[label_, props_] := <|
  "name_input_form" -> toInputString[label],
  "type_input_form" -> toInputString[props[Type]],
  "indices_input_form" -> listInputStrings[props[Indices]],
  "charges_input_form" -> listInputStrings[props[Charges]],
  "self_conjugate" -> boolValue[props[SelfConjugate]],
  "chirality_input_form" -> toInputString[props[Chiral]],
  "mass_input_form" -> toInputString[props[Mass]],
  "heavy" -> boolValue[props[Heavy]],
  "zero_mode" -> boolValue[props[ZeroMode]],
  "field_role" -> fieldRole[props],
  "propagating" -> !boolValue[props[BackgroundField]]
|>;

exportModel[model_String] := Module[
  {lagrangian, state, outFile},
  ResetAll[];
  Matchete`PackageScope`ActivateValidationMode[model, False];

  Begin["Global`"];
  lagrangian = LoadModel[model];
  End[];

  state = <|
    "schema_version" -> 1,
    "kind" -> "matchete_loaded_model_state",
    "generator" -> "export_matchete_model_state.wls",
    "model" -> model,
    "matchete_root" -> matcheteRoot,
    "matchete_runtime_required" -> True,
    "lagrangian_input_form" -> toInputString[lagrangian],
    "flavor_indices" -> entryList[GetFlavorIndices[], flavorEntry],
    "gauge_groups" -> entryList[GetGaugeGroups[], groupEntry["gauge"]],
    "global_groups" -> entryList[GetGlobalGroups[], groupEntry["global"]],
    "representations" -> entryList[GetRepresentations[], representationEntry],
    "cg_tensors" -> (cgEntry /@ Keys[Matchete`PackageScope`$CGproperties]),
    "couplings" -> entryList[GetCouplings[], couplingEntry],
    "fields" -> entryList[GetFields[], fieldEntry]
  |>;

  outFile = FileNameJoin[{outDir, model <> ".model_state.json"}];
  Export[outFile, state, "RawJSON"];
  Print["Wrote ", outFile];
];

Scan[exportModel, models];
Quit[0];
