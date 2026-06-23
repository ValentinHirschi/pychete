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
