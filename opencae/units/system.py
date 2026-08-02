from dataclasses import dataclass

from .catalog import BASE_CATALOGS
from .common_units import recognized_symbol
from .quantities import BY_KEY, Quantity


@dataclass
class UnitSystem:
    name: str
    length: str = "mm"
    force: str = "N"
    time: str = "s"
    temperature: str = "°C"

    def to_dict(self):
        return {"name": self.name, "length": self.length, "force": self.force, "time": self.time, "temperature": self.temperature}

    @classmethod
    def from_dict(cls, values):
        return cls(**{key: values.get(key, default) for key, default in cls("Units").to_dict().items()})

    def base(self, key):
        return BASE_CATALOGS[key][getattr(self, key)]

    def scale(self, quantity: str | Quantity) -> float:
        item = BY_KEY[quantity] if isinstance(quantity, str) else quantity
        l, f, t, temp = item.dimensions
        return self.base("length").scale ** l * self.base("force").scale ** f * self.base("time").scale ** t * self.base("temperature").scale ** temp

    def symbol(self, quantity: str | Quantity) -> str:
        item = BY_KEY[quantity] if isinstance(quantity, str) else quantity
        if item.key == "temperature": return self.temperature
        common = recognized_symbol(item.key, self.scale(item))
        return common or self._composite_symbol(item.dimensions)

    def conversion_to(self, target, quantity: str | Quantity) -> tuple[float, float]:
        item = BY_KEY[quantity] if isinstance(quantity, str) else quantity
        if item.key != "temperature": return self.scale(item) / target.scale(item), 0.0
        source, dest = self.base("temperature"), target.base("temperature")
        return source.scale / dest.scale, (source.offset - dest.offset) / dest.scale

    def _composite_symbol(self, dimensions):
        symbols = (self.length, self.force, self.time, self.temperature)
        numerator, denominator = [], []
        for symbol, exponent in zip(symbols, dimensions):
            if not exponent: continue
            target = numerator if exponent > 0 else denominator
            powers = {2: "²", 3: "³", 4: "⁴"}; power = powers.get(abs(exponent), f"^{abs(exponent)}")
            target.append(symbol if abs(exponent) == 1 else f"{symbol}{power}")
        top = "·".join(numerator) or "1"; bottom = "·".join(denominator)
        return top if not bottom else f"{top}/{bottom}"
