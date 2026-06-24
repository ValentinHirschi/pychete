#!/usr/bin/env wolframscript
(* ::Package:: *)

(* Optional user-facing wrapper for the raw Matchete matching snapshot exporter.

   This script intentionally delegates to the maintained helper implementation.
   It is a convenience route for users who have Mathematica and Matchete
   available; pychete runtime code and pytest remain independent of both.
*)

args = Rest @ $ScriptCommandLine;
repoRoot = DirectoryName[DirectoryName[$InputFileName]];
helper = FileNameJoin[{repoRoot, "helper_mathematica_scripts", "export_matchete_matching_snapshots.wls"}];

If[!FileExistsQ[helper],
  Print["Matchete matching-snapshot helper not found: ", helper];
  Quit[2];
];

proc = RunProcess[Join[{"wolframscript", "-file", helper}, args], All];
WriteString["stdout", proc["StandardOutput"]];
WriteString["stderr", proc["StandardError"]];
Quit[proc["ExitCode"]];
