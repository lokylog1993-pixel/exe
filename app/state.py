
from __future__ import annotations
import json, os, re
from typing import Dict, Any, List

DEFAULT_PATH = os.getenv("BITD_STATE_PATH", "data/state.json")

DEFAULT_ACTIONS = [
    "Hunt","Study","Survey","Tinker",
    "Finesse","Prowl","Skirmish","Wreck",
    "Command","Consort","Sway","Attune"
]

# Trigger presets
TRIG_PRESETS = {
    "Стандарт": [
        {"pattern": "перестрелк", "position": "Рискованная", "effect": "Обычный"},
        {"pattern": "взлом|замок|отмыч", "position": "Рискованная", "effect": "Низкий"},
        {"pattern": "переговор|уговор|шантаж", "position": "Контролируемая", "effect": "Обычный"},
        {"pattern": "скрытн|прокра", "position": "Рискованная", "effect": "Обычный"},
        {"pattern": "ритуал|призрак|дьявол", "position": "Отчаянная", "effect": "Высокий"}
    ],
    "Оккульт": [
        {"pattern": "ритуал|призрак|дьявол|тьма|эфир", "position": "Отчаянная", "effect": "Высокий"},
        {"pattern": "знани|исслед", "position": "Контролируемая", "effect": "Обычный"},
        {"pattern": "оскверн|проклят", "position": "Рискованная", "effect": "Высокий"}
    ],
    "Дипломатия": [
        {"pattern": "переговор|шантаж|уговор|сделк", "position": "Контролируемая", "effect": "Обычный"},
        {"pattern": "публика|толпа|рынок", "position": "Рискованная", "effect": "Низкий"},
        {"pattern": "аристократ|совет|чиновник", "position": "Рискованная", "effect": "Обычный"}
    ],
    "Взлом": [
        {"pattern": "замок|отмыч|механизм|дверь", "position": "Рискованная", "effect": "Низкий"},
        {"pattern": "инструмент|паяль|взрыв", "position": "Отчаянная", "effect": "Высокий"},
        {"pattern": "скрытн|ночью|стража", "position": "Рискованная", "effect": "Обычный"}
    ]
}

DEFAULT_CONSEQUENCES = {
    "Отчаянная": {
        "bad": ["Тяжёлое ранение (harm 3)", "Заполнить вражд. часы:2", "Эскалация угрозы (алярм/рейнфорс)", "Heat +2"],
        "partial": ["Среднее ранение (harm 2)", "Компликация (временный -1d)", "Заполнить вражд. часы:1"]
    },
    "Рискованная": {
        "bad": ["Среднее ранение (harm 2)", "Потеря позиции", "Heat +1", "Час угрозы +2"],
        "partial": ["Лёгкое ранение (harm 1)", "Компликация на сцене", "Час угрозы +1"]
    },
    "Контролируемая": {
        "bad": ["Лёгкое ранение (harm 1)", "Отступление/потеря преимущества", "Час угрозы +1"],
        "partial": ["Небольшая заминка", "Временный риск", "Минус ресурс"]
    }
}

def default_campaign():
    return {
        "players": {},
        "crew": {"name": "Тени", "playbook": "Shadows", "tier": 0, "hold": "Слабая", "upgrades": {}, "xp": 0, "advances": 0},
        "factions": {},
        "clocks": [],
        "heat": 0, "wanted": 0, "rep": 0, "coin": 2,
        "config": {
            "house_rules": {
                "auto_rep_heat": True,
                "auto_xp_desperate": True,
                "advance_threshold_player": 8,
                "advance_threshold_crew": 8
            },
            "rules": {
                "consequence_presets": {},
                "triggers": TRIG_PRESETS["Стандарт"],
                "consequences": DEFAULT_CONSEQUENCES,
                "trigger_presets": list(TRIG_PRESETS.keys())
            }
        },
        "last_roll": None
    }

class StateStore:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            root = {"current_campaign": "default", "campaigns": {"default": default_campaign()}}
            self.save(root)

    # ---- core io ----
    def load_root(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, root: Dict[str, Any]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(root, f, ensure_ascii=False, indent=2)

    def _get_cur(self, root: Dict[str, Any]) -> Dict[str, Any]:
        cur = root.get("current_campaign", "default")
        return root.setdefault("campaigns", {}).setdefault(cur, default_campaign())

    # ---- campaigns ----
    def create_campaign(self, name: str) -> None:
        root = self.load_root()
        root.setdefault("campaigns", {})
        root["campaigns"][name] = default_campaign()
        root["current_campaign"] = name
        self.save(root)

    def switch_campaign(self, name: str) -> None:
        root = self.load_root()
        if name not in root.get("campaigns", {}):
            raise ValueError("Кампания не найдена")
        root["current_campaign"] = name
        self.save(root)

    def list_campaigns(self) -> List[str]:
        root = self.load_root()
        return list(root.get("campaigns", {}).keys())

    # ---- current get/save ----
    def get(self) -> Dict[str, Any]:
        root = self.load_root()
        cur_name = root.get("current_campaign", "default")
        cur = self._get_cur(root)
        return {"current_campaign": cur_name, **cur}

    def save_current(self, cur: Dict[str, Any]) -> None:
        root = self.load_root()
        root["campaigns"][root.get("current_campaign","default")] = cur
        self.save(root)

    # ---------- clocks ----------
    def upsert_clock(self, name: str, segments: int) -> None:
        cur = self.get()
        for c in cur["clocks"]:
            if c["name"] == name:
                c["segments"] = segments
                self.save_current(cur); return
        cur["clocks"].append({"name": name, "segments": segments, "filled": 0})
        self.save_current(cur)

    def fill_clock(self, name: str, n: int) -> None:
        cur = self.get()
        for c in cur["clocks"]:
            if c["name"] == name:
                c["filled"] = min(c["segments"], c["filled"] + n)
                self.save_current(cur); return
        raise ValueError(f"Clock '{name}' not found")

    # ---------- meta ----------
    def set_meta(self, **kwargs):
        cur = self.get()
        for k in ["heat", "wanted", "rep", "coin"]:
            if k in kwargs and kwargs[k] is not None:
                cur[k] = int(kwargs[k])
        self.save_current(cur)

    def add_rep(self, n: int):
        cur = self.get()
        cur["rep"] = int(cur.get("rep",0)) + int(n)
        self.save_current(cur)

    def add_heat(self, n: int):
        cur = self.get()
        cur["heat"] = int(cur.get("heat",0)) + int(n)
        self.save_current(cur)

    # ---------- players ----------
    def upsert_player(self, name: str):
        cur = self.get()
        cur.setdefault("players", {})
        if name not in cur["players"]:
            cur["players"][name] = {
                "harms": [],
                "actions": {a: 0 for a in DEFAULT_ACTIONS},
                "stress": 0, "trauma": [], "pending_trauma": 0, "xp": 0, "advances": 0
            }
            self.save_current(cur)

    def set_action(self, name: str, action: str, rating: int):
        cur = self.get()
        self.upsert_player(name)
        cur = self.get()
        cur["players"][name]["actions"][action] = int(rating)
        self.save_current(cur)

    def get_action(self, name: str, action: str) -> int:
        cur = self.get()
        return int(cur.get("players", {}).get(name, {}).get("actions", {}).get(action, 0))

    def set_stress(self, name: str, stress: int):
        cur = self.get()
        self.upsert_player(name)
        cur = self.get()
        stress = int(stress)
        if stress > 9:
            cur["players"][name]["pending_trauma"] = int(cur["players"][name].get("pending_trauma",0)) + 1
            stress = 0
        cur["players"][name]["stress"] = max(0, min(9, stress))
        self.save_current(cur)

    def add_trauma(self, name: str, label: str):
        cur = self.get()
        self.upsert_player(name)
        cur = self.get()
        tr = cur["players"][name].setdefault("trauma", [])
        if label and label not in tr:
            tr.append(label)
        self.save_current(cur)

    def consume_pending_trauma(self, name: str, label: str):
        cur = self.get()
        self.upsert_player(name)
        cur = self.get()
        pt = int(cur["players"][name].get("pending_trauma", 0))
        if pt <= 0:
            return
        cur["players"][name]["pending_trauma"] = pt - 1
        if label:
            tr = cur["players"][name].setdefault("trauma", [])
            if label not in tr:
                tr.append(label)
        self.save_current(cur)

    def _advance_rollover(self, cur: Dict[str, Any], who: str, is_crew: bool = False):
        if is_crew:
            th = int(cur["config"]["house_rules"].get("advance_threshold_crew", 8))
            xp = int(cur["crew"].get("xp", 0))
            adv = int(cur["crew"].get("advances", 0))
            if xp >= th:
                adv_add = xp // th
                cur["crew"]["advances"] = adv + adv_add
                cur["crew"]["xp"] = xp % th
        else:
            th = int(cur["config"]["house_rules"].get("advance_threshold_player", 8))
            xp = int(cur["players"][who].get("xp", 0))
            adv = int(cur["players"][who].get("advances", 0))
            if xp >= th:
                adv_add = xp // th
                cur["players"][who]["advances"] = adv + adv_add
                cur["players"][who]["xp"] = xp % th

    def add_player_xp(self, name: str, n: int):
        cur = self.get()
        self.upsert_player(name)
        cur = self.get()
        cur["players"][name]["xp"] = int(cur["players"][name].get("xp",0)) + int(n)
        self._advance_rollover(cur, name, is_crew=False)
        self.save_current(cur)

    def add_crew_xp(self, n: int):
        cur = self.get()
        cur["crew"]["xp"] = int(cur["crew"].get("xp",0)) + int(n)
        self._advance_rollover(cur, who="", is_crew=True)
        self.save_current(cur)

    # ---------- crew ----------
    def set_crew(self, name: str | None=None, playbook: str | None=None, tier: int | None=None, hold: str | None=None, upgrades: dict | None=None):
        cur = self.get()
        if name is not None: cur["crew"]["name"] = name
        if playbook is not None: cur["crew"]["playbook"] = playbook
        if tier is not None: cur["crew"]["tier"] = int(tier)
        if hold is not None: cur["crew"]["hold"] = hold
        if upgrades is not None: cur["crew"]["upgrades"] = upgrades
        self.save_current(cur)

    # ---------- factions ----------
    def faction_upsert(self, name: str):
        cur = self.get()
        facs = cur.setdefault("factions", {})
        facs.setdefault(name, {"status": 0, "clocks": []})
        self.save_current(cur)

    def faction_set_status(self, name: str, status: int):
        cur = self.get()
        self.faction_upsert(name)
        cur = self.get()
        cur["factions"][name]["status"] = int(status)
        self.save_current(cur)

    def faction_clock_create(self, name: str, clock: str, segments: int):
        cur = self.get()
        self.faction_upsert(name)
        cur = self.get()
        clocks = cur["factions"][name].setdefault("clocks", [])
        for c in clocks:
            if c["name"] == clock:
                c["segments"] = int(segments)
                self.save_current(cur); return
        clocks.append({"name": clock, "segments": int(segments), "filled": 0})
        self.save_current(cur)

    def faction_clock_fill(self, name: str, clock: str, n: int):
        cur = self.get()
        self.faction_upsert(name)
        cur = self.get()
        for c in cur["factions"][name].setdefault("clocks", []):
            if c["name"] == clock:
                c["filled"] = min(c["segments"], c["filled"] + int(n))
                self.save_current(cur); return
        raise ValueError("Clock not found")

    # ---------- rules & suggestions ----------
    def use_trigger_preset(self, name: str):
        cur = self.get()
        if name not in TRIG_PRESETS:
            raise ValueError("Неизвестный пресет")
        cur["config"]["rules"]["triggers"] = TRIG_PRESETS[name]
        self.save_current(cur)

    def set_thresholds(self, player: int | None=None, crew: int | None=None):
        cur = self.get()
        if player is not None:
            cur["config"]["house_rules"]["advance_threshold_player"] = int(player)
        if crew is not None:
            cur["config"]["house_rules"]["advance_threshold_crew"] = int(crew)
        self.save_current(cur)

    def consequence_suggest(self, position: str, quality: str):
        cur = self.get()
        cons = cur.get("config", {}).get("rules", {}).get("consequences", DEFAULT_CONSEQUENCES)
        pos = cons.get(position) or cons.get("Рискованная", {})
        key = "partial" if quality == "partial" else "bad"
        return pos.get(key, [])

    # ---------- last roll ----------
    def set_last_roll(self, payload: Dict[str, Any] | None):
        cur = self.get()
        cur["last_roll"] = payload
        self.save_current(cur)

    # ---------- import/export ----------
    def export_state(self) -> Dict[str, Any]:
        return self.get()

    def import_state(self, payload: Dict[str, Any]):
        if not isinstance(payload, dict):
            raise ValueError("Неверный формат")
        cur_name = payload.get("current_campaign", "imported")
        root = self.load_root()
        root.setdefault("campaigns", {})
        root["campaigns"][cur_name] = {k:v for k,v in payload.items() if k != "current_campaign"}
        root["current_campaign"] = cur_name
        self.save(root)


    # ---------- harms ----------
    def add_harm(self, name: str, level: int, label: str, kind: str | None=None):
        cur = self.get()
        self.upsert_player(name)
        cur = self.get()
        h = cur["players"][name].setdefault("harms", [])
        h.append({"level": int(level), "label": label, "kind": (kind or "generic")})
        self.save_current(cur)

    def clear_harm(self, name: str, idx: int):
        cur = self.get()
        self.upsert_player(name)
        cur = self.get()
        harms = cur["players"][name].setdefault("harms", [])
        if 0 <= int(idx) < len(harms):
            harms.pop(int(idx))
        self.save_current(cur)


    def harm_penalty(self, name: str) -> int:
        """Дом-правило: уровень 3 даёт -2d, уровень 2 даёт -1d, уровень 1 не даёт штраф.
        Берём худший из имеющихся ран."""
        try:
            cur = self.get()
            harms = cur.get("players", {}).get(name, {}).get("harms", [])
            worst = 0
            for h in harms:
                lvl = int(h.get("level", 0) or 0)
                if lvl > worst: worst = lvl
            if worst >= 3: return 2
            if worst >= 2: return 1
            return 0
        except Exception:
            return 0

    def add_last_roll_suggestion(self, line: str):
        cur = self.get()
        if not cur.get("last_roll"):
            return
        cons = cur["last_roll"].setdefault("consequences", [])
        if line and line not in cons:
            cons.append(line)
        self.save_current(cur)


    def list_harms(self, name: str):
        cur = self.get()
        return cur.get("players", {}).get(name, {}).get("harms", [])

    def save_scene_consequence_preset(self, name: str):
        cur = self.get()
        lr = cur.get("last_roll") or {}
        lines = lr.get("consequences", [])
        pres = cur["config"]["rules"].setdefault("consequence_presets", {})
        pres[name] = list(lines)
        self.save_current(cur)

    def apply_scene_consequence_preset(self, name: str):
        cur = self.get()
        pres = cur.get("config", {}).get("rules", {}).get("consequence_presets", {})
        lines = pres.get(name, [])
        if not cur.get("last_roll"):
            cur["last_roll"] = {"kind":"system"}
        cur["last_roll"]["consequences"] = list(lines)
        self.save_current(cur)

    def list_scene_consequence_presets(self):
        cur = self.get()
        return list(cur.get("config", {}).get("rules", {}).get("consequence_presets", {}).keys())
