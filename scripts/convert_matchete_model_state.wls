#!/usr/bin/env wolframscript
(* ::Package:: *)

(* Optional one-command Matchete model-state conversion wrapper.

   This script is for users who have Mathematica and the read-only Matchete
   reference checkout available. It exports loaded Matchete model state and
   immediately converts the RawJSON output into pychete-owned fixtures.

   Runtime pychete code and pytest must not call this script or require
   Mathematica, wolframscript, or Matchete.
*)

args = Rest @ $ScriptCommandLine;
repoRoot = DirectoryName[DirectoryName[$InputFileName]];

optionValue[name_String, default_String] := Module[{pos},
  pos = FirstPosition[args, "--" <> name, Missing["NotFound"], {1}, Heads -> False];
  If[pos === Missing["NotFound"] || Length[args] < pos[[1]] + 1,
    default,
    args[[pos[[1]] + 1]]
  ]
];

hasFlag[name_String] := MemberQ[args, "--" <> name];

absolutePath[path_String] := If[
  StringStartsQ[path, "/"],
  path,
  FileNameJoin[{repoRoot, path}]
];

scriptPath[name_String] := FileNameJoin[{repoRoot, "scripts", name}];

defaultModels = "VLF_toy_model,Singlet_Scalar_Extension,E_VLL,S1S3LQs";
rawOut = absolutePath @ optionValue[
  "raw-out",
  FileNameJoin[{"assets", "validation", "matchete", "model_state"}]
];
fixturesDir = absolutePath @ optionValue[
  "fixtures-dir",
  FileNameJoin[{"assets", "validation", "pychete"}]
];
modelsText = optionValue["models", defaultModels];
python = optionValue[
  "python",
  If[
    FileExistsQ[FileNameJoin[{repoRoot, "dependencies", ".venv", "bin", "python"}]],
    FileNameJoin[{repoRoot, "dependencies", ".venv", "bin", "python"}],
    "python3"
  ]
];

exporter = scriptPath["export_matchete_model_state.wls"];
converter = scriptPath["convert_matchete_model_state.py"];

If[!FileExistsQ[exporter],
  Print["Matchete model-state exporter wrapper not found: ", exporter];
  Quit[2];
];
If[!FileExistsQ[converter],
  Print["Matchete model-state converter wrapper not found: ", converter];
  Quit[2];
];

models = Select[StringTrim /@ StringSplit[modelsText, ","], StringLength[#] > 0 &];
If[Length[models] == 0,
  Print["No models requested."];
  Quit[2];
];

exportProc = RunProcess[
  {"wolframscript", "-file", exporter, "--out", rawOut, "--models", modelsText},
  All
];
WriteString["stdout", exportProc["StandardOutput"]];
WriteString["stderr", exportProc["StandardError"]];
If[exportProc["ExitCode"] != 0, Quit[exportProc["ExitCode"]]];

inputFiles = FileNameJoin[{rawOut, # <> ".model_state.json"}] & /@ models;
missing = Select[inputFiles, !FileExistsQ[#] &];
If[Length[missing] > 0,
  Print["Missing exported model-state file(s): ", StringRiffle[missing, ", "]];
  Quit[2];
];

convertArgs = Join[
  {"env", "PYTHONPATH=" <> FileNameJoin[{repoRoot, "src"}], python, converter},
  inputFiles,
  {"--fixtures-dir", fixturesDir}
];
If[hasFlag["no-lagrangian"], convertArgs = Join[convertArgs, {"--no-lagrangian"}]];

convertProc = RunProcess[convertArgs, All];
WriteString["stdout", convertProc["StandardOutput"]];
WriteString["stderr", convertProc["StandardError"]];
Quit[convertProc["ExitCode"]];
