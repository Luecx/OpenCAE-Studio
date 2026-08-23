# OpenCAE ViewCube visibility test

This isolated Qt window renders the same camera-oriented beveled ViewCube used
by OpenCAE without starting VTK, PyVista, or an OpenGL viewport.

From the repository root, run:

```bash
python3 -m view_cube_test
```

Expected result:

- a dark grid-like test viewport;
- a clearly visible beveled cube in the upper-right corner;
- no contrasting panel or border behind the cube;
- six large main faces, twelve narrow edge faces, and eight corner triangles;
- live cube rotation while dragging the viewport background;
- blue hover feedback on main, edge, and corner faces;
- a world-space direction after clicking any visible face.

The prototype paints an opaque widget surface intentionally. It does not use
`WA_TranslucentBackground`, because translucent Qt widgets above native OpenGL
children are composed inconsistently by some Linux and Windows platform plugins.
