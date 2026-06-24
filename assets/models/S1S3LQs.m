(* ::Package:: *)

(* ::Title:: *)
(*S1-S3 LQ model file*)


(* ::Subtitle:: *)
(*SM extension with two scalar leptoquarks: S1~(3bar,1,1/3) and S1~(3bar,3,1/3)*)


ParentModel["SM"]


DefineField[S1, Scalar, Indices-> Bar@ SU3c[fund], Charges-> U1Y[1/3], Mass->{Heavy, M1}];
DefineField[S3, Scalar, Indices-> {Bar@ SU3c[fund], SU2L[adj]}, Charges-> U1Y[1/3],
	Mass-> {Heavy, M3}];


DefineCoupling[y1L, Indices-> {Flavor, Flavor}];
DefineCoupling[y1R, Indices-> {Flavor, Flavor}];
DefineCoupling[y3L, Indices-> {Flavor, Flavor}];


DefineCoupling[\[Lambda]H1, SelfConjugate-> True];
DefineCoupling[\[Lambda]H3, SelfConjugate-> True];
DefineCoupling[\[Lambda]H13];
DefineCoupling[\[Lambda]H3p, SelfConjugate-> True];


Module[{p,r,i,j,k,J,K,L,\[Alpha],\[Tau]SU2L,fSU2L,\[Epsilon]SU2L,S1Lag,S3Lag,S1S3Lag},
	\[Tau]SU2L[Jadj_,ifund_,jfund_]:= 2 CG[gen[SU2L[fund]],{Jadj,ifund,jfund}];
	fSU2L[Iadj_,Jadj_,Kadj_]:=CG[fStruct[SU2L],{Iadj,Jadj,Kadj}];
	\[Epsilon]SU2L[ifund_,jfund_]:= CG[eps[SU2L],{ifund,jfund}];

	S1Lag = FreeLag[S1] + PlusHc[y1L[p,r] S1[\[Alpha]] Bar@\[Epsilon]SU2L[i,j] Bar@CConj@q[\[Alpha],i,p]**l[j,r] + y1R[p,r] S1[\[Alpha]] Bar@CConj@u[\[Alpha],p]**e[r]] - \[Lambda]H1[] Bar@H[i] H[i] Bar@S1[\[Alpha]] S1[\[Alpha]];
	S3Lag = FreeLag[S3] + PlusHc[y3L[p,r] Bar@\[Epsilon]SU2L[i,j] \[Tau]SU2L[J,j,k] S3[\[Alpha],J] Bar@CConj@q[\[Alpha],i,p]**l[k,r]] - \[Lambda]H3[] Bar@H[i] H[i] Bar@S3[\[Alpha],J] S3[\[Alpha],J] - I \[Lambda]H3p[] fSU2L[J,K,L] Bar@H[i] \[Tau]SU2L[J,i,j] H[j] Bar@S3[\[Alpha],K] S3[\[Alpha],L];
	S1S3Lag = - PlusHc[\[Lambda]H13[] Bar@H[i] \[Tau]SU2L[J,i,j] H[j] Bar@S3[\[Alpha],J] S1[\[Alpha]]];

	S1Lag + S3Lag + S1S3Lag//RelabelIndices
]
