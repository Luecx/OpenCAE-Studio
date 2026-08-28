# OpenCAE Studio 0.15.2

OpenCAE Studio is a Qt/PyVista-based CAE pre- and post-processing application.
This version keeps the generic region architecture from 0.15.x while simplifying
all normal region fields to a compact, predictable selection workflow.

## Installation

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

## Run

```bash
python main.py
```

## Compact region selection

Normal dialogs show only:

```text
[ Select in View ] [ Extended… ]
4 objects selected
```

- `Select in View` starts the field-specific viewport picker.
- The button remains checked and highlighted while its session is active.
- Starting another field automatically finishes the previous session.
- A normal click replaces a multi-region selection, Shift adds and Ctrl removes.
- `Extended…` opens the detailed operand table with Add Region, Remove, Clear and
  Save as Region.
- Geometry-to-mesh projection is not performed while picking. Validation and
  resolution happen on Apply/OK.

Coupling and rigid-body control points are intentionally simpler:

- only a geometry vertex, reference point or mesh node is accepted;
- named sets/regions are not accepted as the control point;
- the first valid point ends the pick session automatically;
- the selected label and world position remain visible in the dialog;
- a persistent viewport marker remains visible until the dialog is closed or
  the selection is replaced.

Coupled regions, section assignments, loads, supports, seeds, mesh controls,
element controls and partition targets use the compact selector. The full table
remains available in `Extended…` and in the dedicated named-region editor.

## Region model

All reusable and inline targets are represented by one `RegionDefinition`. A
definition may combine CAD entities, mesh entities, reference points and named
region occurrences. Consumers request node, element, facet or single-control-node
projection from the central `RegionResolver` only when the dialog is applied.

## Tests

```bash
python -m pytest -q
```

Native Qt/PyVista interaction requires the packages in `requirements.txt` and a
graphical environment.
