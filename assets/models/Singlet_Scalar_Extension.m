(* ::Package:: *)

(* ::Title:: *)
(*Singlet Scalar Extension model file*)


(* ::Subtitle:: *)
(*SM extension with a singlet scalar ~ (1,1,0)*)


ParentModel["SM"]


DefineField[\[Phi], Scalar, SelfConjugate->True, Mass->{Heavy, M}];


DefineCoupling[A, SelfConjugate->True];
DefineCoupling[\[Kappa], SelfConjugate->True];
DefineCoupling[\[Mu]\[Phi], SelfConjugate->True];
DefineCoupling[\[Lambda]\[Phi], SelfConjugate->True];


Module[{i,Lint},
	Lint = -A[]Bar@H[i]H[i]\[Phi][]-1/2 \[Kappa][]Bar@H[i]H[i]\[Phi][]\[Phi][]- 1/3! \[Mu]\[Phi][]\[Phi][]^3-1/4! \[Lambda]\[Phi][]\[Phi][]^4;

	FreeLag[\[Phi]] + Lint //RelabelIndices
]
