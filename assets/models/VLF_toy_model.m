(* ::Package:: *)

(* ::Title:: *)
(*Vector-like fermions toy model file*)

(* ::Subtitle:: *)
(*Toy model with a heavy vector-like fermion*)

(* ::Section:: *)
(*Lagrangian*)

DefineGaugeGroup[U1e, U1, e, A];


DefineField[\[CapitalPsi], Fermion, Charges-> {U1e[1]}, Mass-> {Heavy, M}];
DefineField[\[Psi], Fermion, Charges-> {U1e[1]}, Mass-> 0];
DefineField[\[Phi], Scalar, Mass-> {Light, m}, SelfConjugate-> True];


DefineCoupling[y];


Module[{Lint},
	Lint = -y[] Bar@\[Psi][]** PR** \[CapitalPsi][] \[Phi][];

	FreeLag[A, \[CapitalPsi], \[Psi], \[Phi]] + PlusHc[Lint] //RelabelIndices
]
