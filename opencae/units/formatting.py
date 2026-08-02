def number(value: float) -> str:
    absolute = abs(value)
    if value == 0: return "0"
    if absolute >= 1e5 or absolute < 1e-4: return f"{value:.6g}"
    return f"{value:.8g}"


def conversion_text(scale: float, offset: float) -> str:
    if abs(offset) < 1e-12: return f"× {number(scale)}"
    sign = "+" if offset >= 0 else "−"
    return f"× {number(scale)} {sign} {number(abs(offset))}"
