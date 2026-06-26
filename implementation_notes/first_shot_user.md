# First implementation prompts

## 2026-06-23

> OK we are now starting the real first implementation of pychete.
>
> For all this first implementation store my prompts in `./implementation_notes/first_shot_user.md` and keep all your progress up to data at all times in `./implementation_notes/first_shot_implementation.md`.
>
> Your first task is to do a *VERY DEEP DIVE* into the Mathematica reference implementation to identify what would be a good structure to adopt in python where the workhorse will be symbolica expressions.
>
> In general, do not be afraid to over-engineer the python code and its abstraction and split the implementation not only into different python files but also in python submodules for the various tasks to perform.
>
> However, for now you should plan for how to design the top-level python object that will mimick the top-level associationMaps/data structure that Machete employs to represent lagrangian, fields, representation etc... but do a search yourself and come up with what would be the structures to capture at this point.
> However be mindful that as much as possible should be encoded *DIRECTLY IN THE SYMBOLLICA EXPRESSIONS" and not as python structures. Python structures are fine in some warranted case, but more often than not you should adopt conventions for the symbolica function head, variable names etc..
> Also , do *NOT* always use string parsing to build expressions, but instead use a global store in smtg like utils.py which contains *ALL* the symbolica symbols ever used in pychete and then reference them to build expressions. I.e. do not do *E("phi(flavor(quark),b)")* but instead have those symbols fetched fromt he global store "s" and then do `s.phi(s.flavor(s.quark),S("b"))` , i.e. only use string parsing when it's clear it won't ever be reused. Same for pattern matching placeholder. Also update AGENTS.md with these guidelines.
>
> Ok, with this in mind, the first goal will be as follows:
>
> a) Keep in mind that ultimately we will want support for the full complicstion of SMEFT BSM subtelties (gamma algebra, multi-fermion interactions etc...) but for now let's make sure we can represent with what you will have come up with a simple scalar phi^4 lagrangian. The corresponding tests in Mathematica will then be in `../validation/Definitions.m` and you should replicate them in pychete in the tests directory (also structure it with additional subfolders for the various type of tests we will consider throughout this port).
> Of course, only implement the tests that are relevant to the limited scope of this first implementation.
>
> b) Also consider implementing support for generic indices (flavour and Lorentz)/group theory aspects/dummy. Think about a really good abstraction as more group indices may show up later (see Indices.m).
> Make sure you can use the same top-level inputs as mathematica machete, in particular the vlf toy model file, and you can organise tests around loading VLFToyModel.m. Use the ability of Symbolica to parse Mathematica expressions and convert them to your internal representation. Also make sure any resources (such as this model file) you actually need in pychete is moved to a top-level assets directory and not kept in "read-only" matchete directory. However, except for input material, you can *never* depend on mathematica code in Matchete. For all gamma algebra and colour algebra treatment make sure to use existing routines in idenso. If you need extensions beyond what idenso provides then feel free to implement your own fall back based on Symbolica replacement rules and other capabilities in a subfolder of pychete called "group_algebra" (see "group_magic" for possibly useful reference in the Matchete mathematica reference).
>
> c) Find the equations of motions for a heavy scalar field and be able to integrate it out at tree-level using functional methods (DO NOT work of memory or using online resources but really consult the reference mathematica implementation, in particular ./pychete/Mathematica_reference/Matchete/Package/EFTCounting.m and /pychete/Mathematica_reference/Matchete/Package/FunctionalTools.m.
>
> Do a real solid deep dive in all of the above a come up with an exhaustive plan and ask question wherever ANYTHING is not FULLY CLEAR.

### Follow-ups

> continue

> continue

> establish a plan based on the above with a deep dive reconsiderstio of it based off existing code and then ask question *ANYTHING* unclear

> You seem to be having symbolica license issues, make sure to use the one specified in ~/.bashrc (and load it in the environment variable SYMBOLICA_LICENSE) to avoid all of such issues

> (and add that information to AGENTS.md too)

> OK before you implement the plan, give me a "goal statement" that details all milestones and which I can assign you as goal after you started the implementation of the plan.

> Implement!

> continue

> continue

## 2026-06-25

> Now it is time to extend the current foundation with more basic features so it can start operating on simple toy models and the like. You should store all my prompts for this part in `./implementation_notes/first_shot_user.md` and keep your progress data up to date at all times in `./implementation_notes/first_shot_implementation.md` as before.
>
> The goal today will be to be able to match the VLF toymodel at tree-level.
> This will require support for fermions (cf. NCM.m in Matchete reference material) and Abelian gauge groups. I want you to *very carefully* examine the options in symbolica for implementing the non-commutative structure of the NCM. Most symbols are "commuting" in the sense that they don't live in spinor space, but fermions and gamma matrices are not. I want a NATIVE SYMBOLICA implementation of these features.
> Investigate if we can use spenso to handle the d-dimensional Dirac algebra (cf. DiracAlgebra.m in Matchete reference material). Closely examine if we can get all required features from spenso and point out any potential conflicts so we can make informed decisions.
> The tree-level matching framework should be generalized to handle fermions light and heavy (heavy to be integrated out).
> Make sure that you look at the unit tests in Validation/Tests/ for the original Matchete implementation. Feel free to spin up some wolframscript loading the Matchete package if you need to study how things work in the reference implementation.
>
> Do a real solid deep dive in all of the above a come up with an exhaustive plan and ask question wherever ANYTHING is not FULLY CLEAR. Keep an eye out for anything that doesn't play well with the current architecture in pychete, so we can catch potential problems early.

### VLF follow-ups

> Give me those questions again, I was away

> I'd like more details on the symbolica ncm implmentation.

> Also be sure not to shortcut any questions because I'm not looking. I'd rather get this right than get this quick. That is, *wait for my answers* every time. Add this to AGENT.md

> Ok then. Go ahead and implement

> Oh that reminds me. Formulate a "goal statement" with the milestones for you to work towards as you implement the plan.

> Add a few examples of the VLF model into the jupyter example notebook

> When listing the fields of the toy-model (in the example), you have e.g.
> Psi: type=Fermion            heavy=True  charges=['VLF_toy_model::group_U1e(1)']
> Why is there a string around the group(charge) expression?

> Something is going wrong with the printing (both as_latex and as_symbolica). A numerical factor `-i` get's printed as `-1 i`

> Ok, now I'm observing that the the vlf theory object returned by the python loader has a .dummy_index field. I thought we got rid of this.

> `assert difference.format_plain() == "0"` This cannot be the right way to do this. Clearly we should cast to string to check if an expression vanishes.

> I was insisting on using spenso for the dirac algebra. Looks like I was conflating it with idenso. Perhaps this is more suitable for the d-dimensional (as in 4-2 epsilon) Dirac and Lorentz algebra.

> And what about the spenso_bridge.py? Do we have any dependencies of this somewhere, and should that be changed to an idenso_bridge?

> I want to emphasize that color is not a special group in pychete, we will treat general Lie groups, and so don't want to use time with one special case.

### Dirac algebra validation goal

> If you didn't already, I want you to implement all Dirac-algebra unit tests from Matchete Validation/Test/NCM.wl that cover the current features of the Dirac algebra. Then ensure that they all pass.

> The function is_commutative_spin_factor will be called a lot. We need it to be performant. Fastest check is most likely to check for things that are non-commutative and otherwise default to True (rather than listing the true things individually).

> Why do you have both s.PL/s.PR and s.Proj?

> Sure, get rid of it. But then also treat s.PL/s.PR at the level of _NONCOMMUTATIVE_SPIN_HEADS.

> What version of symbolica are we running here?

> Ok, crucial design question: I've seen that symbolica allows the use of normalization hooks for symbols. This looks like this is the canonical way to treat various "normalization" tasks. Currently there's an explicit call to normalize NCM, but it seems like having this be automated on the symbolica side would be canonical. Any drawbacks of this approach?

> in matching.py we now have HeavyFermionSolution and HeavyScalarSolution. This is largely duplicate code, with more to come. We need to organize it better

> I don't think we need separate wrapper classes just for the fermions to call normalize_ncm as part of normalize solutions. There's no issue in also calling this on scalar fields. It has to be a very cheap function to call or we have a big problem anyway

> You should also call normalize_ncm before expand. NCM is further down towards the leaf of expressions.

> Why do you need to normalize ncm twice?

> Now for the Heavy field solutions. This thing worries me:
> HeavyScalarSolution = HeavyFieldSolution
> HeavyFermionSolution = HeavyFieldSolution
>
> My suspicion is that we can unify a lot (but not all) of the machinery for determining the heavy field solutions. EVentually we'll also add vectors, so might as well unify now

> Some formatting changes for the latex output:
> - covariant derivatives always act on the single field to their immediate right; no parenthesis is needed
> - bars belong only on the field and shouldn't be displayed as a single bar across both fields and derivatives
> - Closed ncm chains should be enclosed in a parenthesis to set it a part from ordinary product factors.

> Much better. Three additional things:
> - A (derivative of a field)-to-some-power should get parenthesis around derivative and field before the power. E.g. the scalar kinetic term would be (D_\mu \phi)^2.
> - If a field has neighboring derivative indices sharing the label, it should be displayed as D^2 \phi rather than D_\mu D_\mu \phi.
> - Order products such that all prefactors (numerics and couplings) appear before, fields, ncm, field-strength tensors etc. In other words, coefficient should come before the operator.

> There's something wrong in the ordering here:
> We need the numerical prefactors, including sign, to appear first.

> Actually, also having the big fraction with a mass in the denominator, isn't so good either. That should be part of the coefficient in front of the operator. The operator part should never appear as part of a fraction, even as a numerator.
