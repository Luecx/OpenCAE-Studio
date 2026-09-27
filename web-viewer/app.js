# OpenCAE Web FRD Viewer

Experimental, zero-backend browser postprocessor for OpenCAE/CalculiX `.frd` result files.

## Run

```bash
python -m http.server 8080 -d web-viewer
```

Then open `http://localhost:8080` and drop an FRD file into the viewport.

## Current prototype

- FRD parsing happens locally in the browser; files are never uploaded.
- Step, frame, field and component selection, including vector magnitude.
- Surface extraction for HEX8, TET4, HEX20 and TET10 solids.
- Classic linear interpolation and quadratic FE shape-function interpolation.
- Auto/manual contour range, color legend, orbit/pan/zoom.
- WebGL2 rasterization. The current prototype tessellates quadratic faces on the CPU; direct GPU FE-basis evaluation is the next rendering milestone.

## Production direction

Move parsing/mesh extraction to a Web Worker/WASM and keep element connectivity plus nodal fields in GPU buffers. Evaluate shape functions directly in WebGPU/WGSL (with a WebGL2 fallback), avoiding CPU-expanded tessellation for large result sets.
