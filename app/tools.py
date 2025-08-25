
from __future__ import annotations
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Literal

Position = Literal["Отчаянная", "Рискованная", "Контролируемая"]
Effect = Literal["Низкий", "Обычный", "Высокий"]

def roll_d6(n: int) -> List[int]:
    if n < 1:
        n = 1  # по правилам всегда бросаем хотя бы 1 куб, беря худший
    return [random.randint(1,6) for _ in range(n)]

def action_outcome(rolls: List[int], zero_die: bool=False) -> Dict:
    if zero_die:
        best = min(rolls)  # ноль кубов — худший из 2
    else:
        best = max(rolls)
    crit = rolls.count(6) >= 2
    if crit:
        quality = "critical"
    elif best == 6:
        quality = "full"
    elif best >= 4:
        quality = "partial"
    else:
        quality = "bad"
    return {"rolls": rolls, "best": best, "quality": quality, "crit": crit}

def action_roll(dice: int) -> Dict:
    zero = dice <= 0
    rolls = roll_d6(2) if zero else roll_d6(dice)
    return action_outcome(rolls, zero_die=zero)

def resistance_roll(dice: int) -> Dict:
    rolls = roll_d6(max(1, dice))
    best = max(rolls)
    stress = max(0, 6 - best)
    return {"rolls": rolls, "best": best, "stress_cost": stress}

def fortune_roll(dice: int) -> Dict:
    return action_roll(dice)

@dataclass
class Clock:
    name: str
    segments: int
    filled: int = 0

    def fill(self, n: int) -> None:
        self.filled = min(self.segments, self.filled + n)

    def to_dict(self):
        return asdict(self)

def effect_to_segments(effect: Effect) -> int:
    return {"Низкий": 1, "Обычный": 2, "Высокий": 3}.get(effect, 2)
