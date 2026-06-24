(* ::Package:: *)

(* ::Title:: *)
(*E VLL model file*)


(* ::Subtitle:: *)
(*SM extension with a a vector-like lepton EE ~ (1,1,-1)*)


ParentModel["SM"]


DefineField[EE, Fermion, Charges-> U1Y[-1], Mass-> {Heavy, ME}, NiceForm-> {"\[ScriptCapitalE]", "\!\(\*SubscriptBox[\(M\), \(\[ScriptCapitalE]\)]\)"}];


DefineCoupling[yE, EFTOrder-> 0, Indices-> Flavor];


Module[{p,i,Lint},
	Lint = -yE[p] Bar@l[i,p]**PR**EE[] H[i];

	FreeLag[EE] + PlusHc[Lint] //RelabelIndices
]
