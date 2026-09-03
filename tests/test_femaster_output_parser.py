"""Regression coverage for structured FEMaster analysis-monitor parsing."""

from opencae.jobs.femaster_output_parser import FEMasterOutputParser


_STEPS = (
    {"name": "Static", "procedure": "Linear Static"},
    {"name": "Nonlinear", "procedure": "Nonlinear Static"},
    {"name": "Buckling", "procedure": "Linear Buckling"},
    {"name": "Topology", "procedure": "Linear Static Topology"},
    {"name": "Modes", "procedure": "Eigenfrequency"},
    {"name": "Transient", "procedure": "Linear Transient"},
    {"name": "Harmonic", "procedure": "Linear Harmonic"},
)


def test_real_femaster_286_patterns_drive_steps_frames_and_post_checks():
    parser = FEMasterOutputParser(_STEPS)

    parser.feed(
        "[INFO] LINEAR STATIC ANALYSIS\n"
        "[INFO] Post-checks\n"
        "[INFO]     [PASS] constraints              : abs = 0.000000e+00\n"
        "[INFO]                                     : rel = 0.000000e+00  <= tol = 1.000000e-10\n"
    )
    details, steps = parser.snapshot()
    assert details["step"] == "Static"
    assert details["procedure"] == "Linear Static"
    assert steps[0]["checks"] == [
        {
            "name": "constraints",
            "status": "PASS",
            "detail": "abs = 0.000000e+00; rel = 0.000000e+00  <= tol = 1.000000e-10",
            "frame": "",
        }
    ]

    # QProcess may split stdout anywhere, including inside a procedure header.
    parser.feed("[INFO] NONLINEAR STATIC ANA")
    parser.feed(
        "LYSIS\n"
        "[INFO]  inc iter      lambda        rel_res          du_norm   ls   asm_ms solve_ms\n"
        "[INFO]    3    2   9.500e-01      5.757e-11      0.000e+00    0        0        0\n"
        "[INFO] Accepted increment 3: lambda = 0.95, Newton iterations = 2, next increment = 0.675\n"
    )
    details, steps = parser.snapshot()
    assert steps[0]["status"] == "PASS"
    assert details["step"] == "Nonlinear"
    assert details["frame"] == "Increment 3"
    assert details["iteration"] == "2"
    assert details["time_frequency"] == "λ = 9.500e-01"
    assert details["state"].startswith("Accepted increment 3")

    parser.feed(
        "[INFO] LINEAR BUCKLING ANALYSIS\n"
        "[INFO] Post-checks\n"
        "[INFO]     [PASS] reduced equilibrium      : abs = 9.853162e-13\n"
        "[INFO]                                     : rel = 9.853162e-16  <= tol = 1.000000e-08\n"
        "[INFO] Buckling summary\n"
        "[INFO]    Idx  Buckling factor lambda\n"
        "[INFO]      1         11523.861534475\n"
        "[INFO]      2         14985.604706932\n"
        "[INFO] Buckling analysis completed.\n"
    )
    details, steps = parser.snapshot()
    assert steps[2]["checks"][0]["frame"] == "Preload"
    assert steps[2]["status"] == "PASS"
    assert details["frame"] == "Mode 2"
    assert details["time_frequency"] == "λ = 14985.604706932"

    parser.feed(
        "[INFO] LINEAR STATIC TOPO\n"
        "[INFO] Post-checks\n"
        "[INFO]     [PASS] null-space (C*T=0)       : abs = 0.000000e+00\n"
        "[INFO]                                     : rel = 0.000000e+00  <= tol = 1.000000e-10\n"
        "[INFO] LINEAR EIGENFREQUENCY ANALYSIS\n"
        "[INFO] Post-checks\n"
        "[INFO]     [PASS] constraints              : abs = 0.000000e+00\n"
        "[INFO]                                     : rel = 0.000000e+00  <= tol = 1.000000e-10\n"
        "[INFO] Post-checks\n"
        "[INFO]     [PASS] reduced equilibrium      : abs = 8.829858e+06\n"
        "[INFO]                                     : rel = 1.000000e+00  <= tol = inf\n"
        "[INFO] Post-checks\n"
        "[INFO]     [PASS] affine consistency (u_p) : abs = 0.000000e+00\n"
        "[INFO]                                     : rel = 0.000000e+00  <= tol = 1.000000e-10\n"
        "[INFO] Eigenfrequency summary\n"
        "[INFO]  Idx          Eigenvalue         Eigenfreq           x       y       z      rx      ry      rz\n"
        "[INFO]    1        8.403192e+08       4613.624737      -0.000   0.000   2.418   0.000   0.000   0.000\n"
        "[INFO]    2        1.104037e+09       5288.249080       0.000   2.386  -0.000   0.000   0.000   0.000\n"
        "[INFO]    3        1.898676e+09       6934.984789       0.000   0.000  -0.000   0.000   0.000   0.000\n"
        "[INFO] Eigenfrequency analysis completed.\n"
    )
    details, steps = parser.snapshot()
    assert steps[3]["status"] == "PASS"
    assert [check["frame"] for check in steps[4]["checks"]] == [
        "Mode 1",
        "Mode 2",
        "Mode 3",
    ]
    assert steps[4]["status"] == "PASS"
    assert details["frame"] == "Mode 3"
    assert details["time_frequency"] == "f = 6934.984789 Hz"

    parser.feed(
        "[INFO] LINEAR TRANSIENT ANALYSIS (Implicit Newmark-β)\n"
        "[INFO]   Starting Newmark time marching (5 steps) ...\n"
        "[INFO]   Newmark step        4/5  t=8.000000e-03 s\n"
    )
    details, _steps = parser.snapshot()
    assert details["step"] == "Transient"
    assert details["procedure"] == "Linear Transient"
    assert details["frame"] == "4 / 5"
    assert details["time_frequency"] == "t = 8.000000e-03 s"
    assert details["state"] == "Time marching"

    parser.feed(
        "[INFO] Transient analysis completed.\n"
        "[INFO] LINEAR HARMONIC RESPONSE ANALYSIS\n"
        "[INFO] Frequency sweep\n"
        "[INFO]    Idx       Frequency     Response norm\n"
        "[INFO]      1       10.000000      3.650826e-03\n"
        "[INFO]     11      500.000000      3.692335e-03\n"
    )
    details, steps = parser.snapshot()
    assert steps[5]["status"] == "Completed"
    assert details["step"] == "Harmonic"
    assert details["frame"] == "Frequency 11"
    assert details["time_frequency"] == "f = 500.000000 Hz"
    assert details["state"] == "Response norm 3.692335e-03"

    parser.finish("Completed")
    details, steps = parser.snapshot()
    assert steps[6]["status"] == "Completed"
    assert details["state"] == "Completed"


def test_failed_process_marks_only_active_step_failed():
    parser = FEMasterOutputParser(_STEPS[:3])
    parser.feed("[INFO] LINEAR STATIC ANALYSIS\n")
    parser.finish("Failed")
    details, steps = parser.snapshot()

    assert details["state"] == "Failed"
    assert steps[0]["status"] == "Failed"
    assert steps[1]["status"] == "Waiting"
    assert steps[2]["status"] == "Waiting"
