(* ::Package:: *)

(* ::Title:: *)
(*SM model file*)


(* ::Text:: *)
(*Gauge groups*)


DefineGaugeGroup[SU3c, SU@3, gs, G,
	FundAlphabet-> CharacterRange["a", "f"],
	AdjAlphabet -> CharacterRange["A", "F"],
	NiceForm->{"\!\(\*SubscriptBox[\(g\), \(s\)]\)", Default},
	UFO-><|"pdg"->21|>];
DefineGaugeGroup[SU2L, SU@2, gL, W,
	FundAlphabet -> CharacterRange["i", "n"],
	AdjAlphabet -> CharacterRange["I", "N"],
	NiceForm->{"\!\(\*SubscriptBox[\(g\), \(L\)]\)", Default}];
DefineGaugeGroup[U1Y, U1, gY, B,
	NiceForm->{"\!\(\*SubscriptBox[\(g\), \(Y\)]\)", Default}];


(* ::Text:: *)
(*Flavor index*)


ParameterDefault[Nf-> 3]


DefineFlavorIndex[Flavor, Nf,
	IndexAlphabet-> {"p", "r", "s", "t", "u", "v"}];


(* ::Text:: *)
(*Matter fields*)


DefineField[q, Fermion, Indices-> {SU3c[fund], SU2L[fund], Flavor},
	Charges->{U1Y[1/6]}, Chiral-> LeftHanded, Mass-> 0];
DefineField[u,Fermion,Indices-> {SU3c[fund], Flavor},
	Charges->{U1Y[2/3]}, Chiral-> RightHanded, Mass-> 0];
DefineField[d,Fermion,Indices-> {SU3c[fund], Flavor},
	Charges->{U1Y[-1/3]}, Chiral-> RightHanded, Mass-> 0];
DefineField[l,Fermion,Indices-> {SU2L[fund], Flavor},
	Charges->{U1Y[-1/2]}, Chiral-> LeftHanded, Mass-> 0];
DefineField[e,Fermion,Indices-> {Flavor},
	Charges->{U1Y[-1]}, Chiral-> RightHanded, Mass-> 0];
DefineField[H, Scalar, Indices-> {SU2L[fund]},
	Charges-> {U1Y[1/2]}, Mass-> 0];


(* ::Text:: *)
(*Couplings*)


DefineCoupling[Yu, Indices-> {Flavor, Flavor},
	NiceForm-> "\!\(\*SubscriptBox[\(Y\), \(u\)]\)"];
DefineCoupling[Yd, Indices-> {Flavor, Flavor},
	NiceForm-> "\!\(\*SubscriptBox[\(Y\), \(d\)]\)"];
DefineCoupling[Ye, Indices-> {Flavor, Flavor},
	NiceForm-> "\!\(\*SubscriptBox[\(Y\), \(e\)]\)"];
(* Mass added as an interaction because it is tachyonic *)
DefineCoupling[\[Mu]2, SelfConjugate-> True, EFTOrder-> 2,
	NiceForm-> "\[Mu]2"];
DefineCoupling[\[Lambda], SelfConjugate->True, EFTOrder-> 0];


(* ::Text:: *)
(*Lagrangian*)


Module[{p,r,s,i,j,\[Alpha],\[Beta],YukawaL,HiggsPotential},

	YukawaL =  Yu[p,r] Bar@q[\[Alpha],i,p]**u[\[Alpha],r] CG[eps[SU2L],{i,j}]Bar@H[j] + Yd[p,r] Bar@q[\[Alpha],i,p]**d[\[Alpha],r]H[i] + Ye[p,r] Bar@l[i,p]**e[r]H[i];
	HiggsPotential = -\[Mu]2[] Bar@H[i]H[i] + \[Lambda][]/2 Bar@H[i]H[i]Bar@H[j]H[j];

	FreeLag[q, u, d, l, e, H, G, W, B] - PlusHc[YukawaL] - HiggsPotential //RelabelIndices
]
