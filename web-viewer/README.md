# OpenCAE Web FRD Viewer

A local-first browser postprocessor for OpenCAE / CalculiX `.frd` result files. The viewer runs entirely in the browser; result files are not uploaded to a backend.

## Run

```bash
python -m http.server 8080 -d web-viewer
```

Open `http://localhost:8080` and drop an FRD file into the viewport or use **Open FRD**.

## Architecture

- `frd-worker.js` — streaming FRD parser, compact node/element indexing, exterior-face extraction, FE-edge and boundary topology.
- `renderer-shaders.js` — WebGL2 FE interpolation, contour, clipping, picking and overlay shaders.
- `renderer-utils.js` — WebGL helpers, matrix/quaternion math, Arcball support and derived nodal values.
- `renderer-base.js` — persistent GPU resources and result/deformation state.
- `renderer.js` — drawing, ID-buffer picking, Arcball navigation, camera views, section plane and screenshots.
- `app.js` — Results UI state, frame navigation/animation, contour/deformation controls, queries, paths and XY plots.

## Implemented viewer features

- Local streaming FRD loading in a Web Worker with a blocking, cancellable progress overlay.
- FRD element types 1–12: linear/quadratic solids, shells and lines.
- Exterior-surface rendering for HEX8/WEDGE6/TET4 and HEX20/WEDGE15/TET10, plus TRI/QUAD shells and line elements.
- GPU FE interpolation in WebGL2 using instanced parametric T3/T6/Q4/Q8 patches. Shape functions are evaluated in the vertex shader; result-field changes do not rebuild CPU tessellated geometry.
- Classic linear corner interpolation fallback.
- Primitive components, `Magnitude` semantics compatible with OpenCAE (`ALL` when supplied by the FRD), and derived von Mises stress.
- Step/frame/field/component navigation, previous/next and frame playback.
- Deformed results, undeformed overlay and automatic deformation scaling for the current frame or all frames in the active step.
- Mesh lines and boundary lines following the displayed/deformed geometry.
- Contour range controls with independent current/all-frame minimum and maximum fits, symmetric range, 2–52 discrete levels (18 default), continuous colors, palettes and below/above-range colors.
- Configurable result colorbar.
- Free quaternion Arcball orbit around a real 3D focal point, visible rotation pivot, middle-button pan, wheel zoom, fit, standard views and scale-preserving perspective/orthographic switching.
- Node and element picking with viewport highlights and result-value summaries.
- Arbitrary section plane with origin/normal, X/Y/Z presets, offset, inversion and optional plane display.
- Mesh-edge paths using solver node IDs and Dijkstra shortest paths on the undeformed FE topology, including quadratic midside segments.
- Path plots and nodal time histories with CSV export.
- Viewport screenshot export.

## Rendering notes

WebGL2 has no hardware tessellation stage. The shape-function path therefore uses a small reusable parametric triangle/quad micro-grid and draws it instanced over exterior FE faces. Per-instance connectivity and nodal positions/results live in GPU textures. Each generated vertex evaluates the corresponding T3/T6/Q4/Q8 FE basis directly on the GPU. This keeps geometry topology persistent while frames/components/ranges change.
