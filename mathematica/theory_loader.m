(* ::Package:: *)

(* Optional pychete helper for exporting Matchete-loaded model state.
   This file may depend on Matchete. Runtime pychete Python code must not. *)

BeginPackage["PycheteTheoryLoader`"];

ExportLoadedTheoryJSON::usage =
  "ExportLoadedTheoryJSON[path, expr] exports a lightweight JSON checkpoint \
from the current Matchete definitions and a Lagrangian expression.";

Begin["`Private`"];

toString[x_] := ToString[InputForm[x]];

ExportLoadedTheoryJSON[path_String, lag_] := Module[{payload},
  payload = <|
    "schema_version" -> 1,
    "source" -> "Matchete",
    "lagrangian_input_form" -> toString[lag],
    "fields" -> If[ValueQ[Matchete`PackageScope`$FieldAssociation],
      AssociationMap[toString, Keys[Matchete`PackageScope`$FieldAssociation]],
      <||>
    ],
    "couplings" -> If[ValueQ[Matchete`PackageScope`$CouplingAssociation],
      AssociationMap[toString, Keys[Matchete`PackageScope`$CouplingAssociation]],
      <||>
    ]
  |>;
  Export[path, payload, "RawJSON"]
];

End[];
EndPackage[];
