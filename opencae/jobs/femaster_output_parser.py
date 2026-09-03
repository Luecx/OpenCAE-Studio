"""Streaming parser for structured FEMaster solver progress and post-checks."""

from __future__ import annotations

from copy import deepcopy
import re


_PROCEDURE_HEADERS = {
    "LINEAR STATIC ANALYSIS": "Linear Static",
    "NONLINEAR STATIC ANALYSIS": "Nonlinear Static",
    "LINEAR BUCKLING ANALYSIS": "Linear Buckling",
    "LINEAR STATIC TOPO": "Linear Static Topology",
    "LINEAR EIGENFREQUENCY ANALYSIS": "Eigenfrequency",
    "LINEAR TRANSIENT ANALYSIS": "Linear Transient",
    "LINEAR HARMONIC RESPONSE ANALYSIS": "Linear Harmonic",
}

_PREFIX = re.compile(r"^\s*\[(?:INFO|WARN|ERROR|DEBUG)\]\s?")
_NONLINEAR_ROW = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+([+\-\d.eE]+)\s+([+\-\d.eE]+)\s+([+\-\d.eE]+)\s+\d+\s+\d+\s+\d+\s*$"
)
_TRANSIENT_STEP = re.compile(
    r"Newmark step\s+(\d+)\s*/\s*(\d+)\s+t=([+\-\d.eE]+)\s*s",
    re.IGNORECASE,
)
_POST_CHECK = re.compile(
    r"^\s*\[([A-Z]+)\]\s+(.+?)\s*:\s*(.+?)\s*$"
)
_POST_CONTINUATION = re.compile(r"^\s*:\s*(.+?)\s*$")
_TABLE_ROW_2 = re.compile(r"^\s*(\d+)\s+([+\-\d.eE]+)\s*$")
_TABLE_ROW_3 = re.compile(
    r"^\s*(\d+)\s+([+\-\d.eE]+)\s+([+\-\d.eE]+)(?:\s+.*)?$"
)


class FEMasterOutputParser:
    """Incrementally derive Analysis-monitor state from FEMaster stdout."""

    def __init__(self, steps=()):
        descriptors = tuple(steps or ())
        self._steps = [
            {
                "name": str(item.get("name", "Step") or "Step"),
                "procedure": str(item.get("procedure", "") or ""),
                "status": "Waiting",
                "checks": [],
            }
            for item in descriptors
        ]
        self._details = {
            "step": "—",
            "procedure": "—",
            "frame": "—",
            "iteration": "—",
            "time_frequency": "—",
            "state": "Waiting",
        }
        self._pending = ""
        self._step_index = -1
        self._procedure = ""
        self._table = ""
        self._in_post_checks = False
        self._current_check = None
        self._modal_post_index = 0
        self._changed = True

    def feed(self, text: str) -> bool:
        """Consume an arbitrary stdout chunk and report structured-state changes."""
        value = self._pending + str(text or "")
        if not value:
            return False
        lines = value.splitlines(keepends=True)
        self._pending = ""
        if lines and not lines[-1].endswith(("\n", "\r")):
            self._pending = lines.pop()
        self._changed = False
        for raw in lines:
            self._consume_line(raw.rstrip("\r\n"))
        return self._changed

    def flush(self) -> bool:
        """Consume a final unterminated line when the process exits."""
        if not self._pending:
            return False
        line, self._pending = self._pending, ""
        self._changed = False
        self._consume_line(line)
        return self._changed

    def finish(self, status: str = "Completed") -> None:
        """Finalize the active step after the solver process terminates."""
        self.flush()
        terminal = str(status or "Completed").strip() or "Completed"
        if self._step_index >= 0:
            if terminal.casefold() == "completed":
                self._complete_step(self._step_index)
            else:
                self._steps[self._step_index]["status"] = terminal
        self._details["state"] = terminal
        self._changed = True

    def snapshot(self) -> tuple[dict, list[dict]]:
        """Return detached structures safe to hand to Qt widgets."""
        return deepcopy(self._details), deepcopy(self._steps)

    def _consume_line(self, raw: str) -> None:
        line = _PREFIX.sub("", raw, count=1).rstrip()
        stripped = line.strip()

        if self._in_post_checks:
            if not stripped:
                return
            match = _POST_CHECK.match(line)
            if match:
                self._append_check(*match.groups())
                return
            continuation = _POST_CONTINUATION.match(line)
            if continuation and self._current_check is not None:
                detail = continuation.group(1).strip()
                previous = str(self._current_check.get("detail", ""))
                self._current_check["detail"] = f"{previous}; {detail}" if previous else detail
                self._changed = True
                return
            self._in_post_checks = False
            self._current_check = None

        procedure = next(
            (
                value
                for header, value in _PROCEDURE_HEADERS.items()
                if stripped.startswith(header)
            ),
            None,
        )
        if procedure is not None:
            self._begin_step(procedure)
            return

        if stripped == "Post-checks":
            self._in_post_checks = True
            self._current_check = None
            if self._procedure == "Eigenfrequency":
                self._modal_post_index += 1
                self._set_details(
                    frame=f"Mode {self._modal_post_index}",
                    iteration="—",
                    time_frequency="—",
                    state=f"Post-checks · Mode {self._modal_post_index}",
                )
            elif self._procedure == "Linear Buckling":
                self._set_details(frame="Preload", state="Post-checks · Preload")
            else:
                self._set_details(state="Post-checks")
            return

        if self._procedure == "Nonlinear Static":
            match = _NONLINEAR_ROW.match(line)
            if match:
                increment, iteration, load_factor, residual, displacement = match.groups()
                self._set_details(
                    frame=f"Increment {increment}",
                    iteration=iteration,
                    time_frequency=f"λ = {load_factor}",
                    state=f"Newton iteration · rel residual {residual} · Δu {displacement}",
                )
                return
            if stripped.startswith("Accepted increment "):
                self._set_details(state=stripped)
                return

        transient = _TRANSIENT_STEP.search(stripped)
        if transient:
            frame, total, time_value = transient.groups()
            self._set_details(
                frame=f"{frame} / {total}",
                iteration="—",
                time_frequency=f"t = {time_value} s",
                state="Time marching",
            )
            return

        if stripped == "Buckling summary":
            self._table = "buckling"
            self._set_details(state="Buckling modes")
            return
        if stripped == "Eigenfrequency summary":
            self._table = "eigen"
            self._set_details(state="Eigenfrequency modes")
            return
        if stripped == "Frequency sweep":
            self._table = "harmonic"
            self._set_details(state="Frequency sweep")
            return

        if self._table == "buckling":
            match = _TABLE_ROW_2.match(line)
            if match:
                index, factor = match.groups()
                self._set_details(
                    frame=f"Mode {index}",
                    iteration="—",
                    time_frequency=f"λ = {factor}",
                    state="Buckling mode",
                )
                return
        elif self._table == "eigen":
            match = _TABLE_ROW_3.match(line)
            if match:
                index, _eigenvalue, frequency = match.groups()
                self._set_details(
                    frame=f"Mode {index}",
                    iteration="—",
                    time_frequency=f"f = {frequency} Hz",
                    state="Eigenfrequency mode",
                )
                return
        elif self._table == "harmonic":
            match = _TABLE_ROW_3.match(line)
            if match:
                index, frequency, response = match.groups()
                self._set_details(
                    frame=f"Frequency {index}",
                    iteration="—",
                    time_frequency=f"f = {frequency} Hz",
                    state=f"Response norm {response}",
                )
                return

        lowered = stripped.casefold()
        if lowered.endswith("analysis completed.") or lowered == "transient analysis completed.":
            if self._step_index >= 0:
                self._complete_step(self._step_index)
            self._set_details(state="Completed")
            self._table = ""

    def _begin_step(self, procedure: str) -> None:
        if self._step_index >= 0:
            self._complete_step(self._step_index)
        self._step_index += 1
        self._procedure = procedure
        self._table = ""
        self._modal_post_index = 0
        if self._step_index >= len(self._steps):
            self._steps.append(
                {
                    "name": f"Step {self._step_index + 1}",
                    "procedure": procedure,
                    "status": "Running",
                    "checks": [],
                }
            )
        step = self._steps[self._step_index]
        step["procedure"] = procedure
        step["status"] = "Running"
        self._set_details(
            step=step["name"],
            procedure=procedure,
            frame="—",
            iteration="—",
            time_frequency="—",
            state="Running",
        )

    def _append_check(self, status: str, name: str, detail: str) -> None:
        if self._step_index < 0:
            return
        frame = ""
        if self._procedure == "Eigenfrequency" and self._modal_post_index:
            frame = f"Mode {self._modal_post_index}"
        elif self._procedure == "Linear Buckling":
            frame = "Preload"
        check = {
            "name": name.strip(),
            "status": status.strip().upper(),
            "detail": detail.strip(),
            "frame": frame,
        }
        self._steps[self._step_index]["checks"].append(check)
        self._current_check = check
        self._changed = True

    def _complete_step(self, index: int) -> None:
        if not (0 <= index < len(self._steps)):
            return
        step = self._steps[index]
        if str(step.get("status", "")).casefold() not in {"running", "waiting"}:
            return
        statuses = [str(item.get("status", "")).upper() for item in step.get("checks", ())]
        if "FAIL" in statuses or "FAILED" in statuses:
            status = "FAIL"
        elif "WARN" in statuses or "WARNING" in statuses:
            status = "WARN"
        elif statuses:
            status = "PASS"
        else:
            status = "Completed"
        step["status"] = status
        self._changed = True

    def _set_details(self, **values) -> None:
        for key, value in values.items():
            normalized = str(value if value not in (None, "") else "—")
            if self._details.get(key) != normalized:
                self._details[key] = normalized
                self._changed = True
