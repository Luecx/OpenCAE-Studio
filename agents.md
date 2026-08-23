# OpenCAE Repository Architecture Rules

This file defines repository-wide implementation rules for OpenCAE Studio. It applies to every file below the repository root unless a more specific `agents.md` is added in a subdirectory.

## 1. Keep responsibilities narrow

- Prefer one cohesive responsibility per module.
- Prefer one top-level class per Python file. Put enums, protocols, dataclasses, and additional classes in their own modules as well when they represent independent concepts.
- Keep files short enough to understand without scrolling through unrelated concerns. As a working target, keep production Python modules below roughly 250 lines; split earlier when responsibilities are already separable.
- If a class becomes large, keep the class in `my_class.py` and move cohesive helper logic to explicit companion modules such as `my_class_validation.py`, `my_class_io.py`, `my_class_factory.py`, or another descriptive `my_class_<responsibility>.py` name.
- Do not create generic `utils.py`, `helpers.py`, or catch-all modules when a responsibility-specific name is possible.
- Controllers orchestrate application flows. They must not also own persistence codecs, solver formatting, filesystem repositories, domain validation, or reusable UI construction.
- Domain model modules must not import Qt/UI code.
- Persistence and migration code belongs under `opencae/persistence`, not inside domain entities.
- Solver-specific export logic belongs under `opencae/solvers` / exporting services, not inside domain aggregates when it can be expressed externally.

## 2. Public model API and references

- `opencae.api` is the user-facing model-authoring boundary. It must remain usable without importing UI code.
- Public API relationships use Python objects, never object names or string keys. Examples: `instance.part is part`, `section.material is material`, and a load targets a region object.
- Persistent references may use stable entity IDs internally. IDs and `EntityRef` are persistence/domain infrastructure and must not leak into ordinary public authoring workflows.
- Never use mutable display names as identity or dictionary keys for cross-entity relationships.
- Renaming an entity must not invalidate references to it.
- Distinguish an actual FEM object from a type/definition. For example, an `Element` owns node objects; an `ElementDefinition` describes mesher/solver element metadata.

## 3. Valid states are explicit

- Do not introduce lifecycle state as arbitrary strings when the set of values is known.
- Use enums or dedicated value objects for states such as job status, mesh status, result availability, source kind, and similar finite domains.
- Store diagnostics such as solver exit codes separately from lifecycle state. Do not encode data in strings such as `"Failed (17)"`.
- Constructors and mutation boundaries should reject impossible combinations early.
- Migration code may accept legacy strings, but normal runtime code should operate on canonical typed states.

## 4. UI templates are centralized

- Reusable visual construction belongs under `opencae/ui/templates` or a focused reusable widget module.
- Do not duplicate margins, spacing, title-label setup, standard button boxes, form-row construction, table setup, or ribbon-button construction in individual dialogs.
- Build larger UI hierarchically from shared primitives: primitive -> control/group -> form/panel -> dialog/ribbon/page.
- `opencae/ui/core` may provide compatibility facades, but new code should prefer the canonical template layer.
- UI modules should collect/emit values and coordinate interaction. Domain validation and model construction should live outside widgets when practical.

## 5. Documentation and comments

- Every production Python module starts with a module docstring describing what the file owns and, when useful, what it deliberately does not own.
- Every public or non-trivial class has a class docstring describing its responsibility and lifecycle.
- Every public or non-trivial function/method has a docstring describing intent, important arguments/results, and relevant invariants.
- Use inline comments to explain *why* a non-obvious step exists, not to restate the code.
- Python inline comments use `#`. Never use `//` as a comment marker; in Python `//` is the floor-division operator.
- Keep comments current when behavior changes. Delete stale comments together with stale code.

## 6. Delete obsolete code

- Prefer deletion over compatibility duplication when a path is no longer used.
- Do not keep prototype applications, shadow modules, duplicate implementations, commented-out blocks, or dead compatibility layers without an active caller or migration requirement.
- A file and a package must not share the same import path (for example both `foo.py` and `foo/`). Such shadow paths are prohibited.
- Before deleting a compatibility path, search the repository for callers and migrate any real users first.

## 7. Imports and dependency direction

The preferred dependency direction is:

`api -> model/domain -> persistence/export adapters`

and for the desktop application:

`ui -> controllers/application services -> model/domain`

Infrastructure may depend on the domain; the domain must not depend on the UI.

- Avoid wildcard imports in new code.
- Package `__init__.py` files are curated public export surfaces, not places for business logic.
- Avoid circular imports by moving shared concepts down to focused domain modules rather than using local imports as the default design.

## 8. Tests and refactors

- Tests should verify behavior and architectural contracts, not exact source-code spelling or implementation layout unless layout is itself the contract.
- Add regression coverage for every bug fixed during a refactor.
- Add architecture tests for important invariants such as forbidden shadow modules or string-based public references when feasible.
- Run compile checks and the maintained regression suite after structural changes.
- Refactors should preserve persisted project compatibility through explicit migrations rather than by spreading legacy handling throughout runtime code.

## 9. Change discipline

Before adding code, ask in this order:

1. Is this code still needed?
2. Which layer owns the responsibility?
3. Is there already a reusable template/service/value object for it?
4. Can the state space be made smaller or typed?
5. Can the implementation be expressed in a shorter, more focused module?

When these rules conflict with a concrete correctness requirement, correctness wins, but document the exception and keep its scope minimal.
