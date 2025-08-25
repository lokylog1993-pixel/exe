
from __future__ import annotations
import json, re, os
from typing import Dict, Any, List

from .llm_backends import LLM, ChatTurn
from .prompts import SYSTEM_PROMPT_RU
from .tools import action_roll, resistance_roll, fortune_roll, effect_to_segments
from .state import StateStore

JSON_BLOCK_RE = re.compile(r"""```json\s*(\{.*?\})\s*```""", re.DOTALL | re.IGNORECASE)

def _truthy(x):
    if isinstance(x, bool): return x
    try:
        if isinstance(x, (int, float)): return x != 0
        if isinstance(x, str): return x.strip().lower() in ("true","1","да","+","y","yes")
    except Exception: pass
    return False

class GMAgent:
    def __init__(self, state: StateStore):
        self.llm = LLM()
        self.state = state

    def _extract_intent(self, text: str):
        m = JSON_BLOCK_RE.search(text)
        intent = None
        if m:
            try:
                intent = json.loads(m.group(1))
            except Exception:
                intent = None
        narration = JSON_BLOCK_RE.sub("", text).strip()
        return intent, narration

    def _dice_from_actor_and_mods(self, actor: str | None, action: str | None, proposed: Dict[str, Any]) -> int:
        # harm penalty
        guess = int(proposed.get("dice_guess", 1))
        base = guess
        if actor and action:
            try:
                base = self.state.get_action(actor, action)
            except Exception:
                base = guess
        bonus = int(proposed.get("bonus", 0) or 0)
        assist = 1 if _truthy(proposed.get("assist")) else 0
        push = 1 if _truthy(proposed.get("push")) else 0
        bargain = 1 if _truthy(proposed.get("bargain")) else 0
        pen = self.state.harm_penalty(actor) if actor else 0
        return int(max(0, base + bonus + assist + push + bargain - pen))

    def _infer_position_effect(self, text: str) -> Dict[str, str] | None:
        try:
            cfg = self.state.get().get("config", {}).get("rules", {})
            triggers = cfg.get("triggers", [])
            t = text.lower()
            for rule in triggers:
                patt = rule.get("pattern", "")
                if patt and re.search(patt, t):
                    return {"position": rule.get("position"), "effect": rule.get("effect"), "from": patt}
        except Exception:
            return None
        return None

    def _apply_house_rep_heat(self, quality: str):
        st = self.state.get()
        if not st.get("config", {}).get("house_rules", {}).get("auto_rep_heat", True):
            return
        if quality == "critical":
            self.state.add_rep(2)
        elif quality == "full":
            self.state.add_rep(1)
        elif quality == "partial":
            self.state.add_heat(1)
        elif quality == "bad":
            self.state.add_heat(2)

    def _apply_house_xp(self, position: str | None, actor: str | None, quality: str | None):
        st = self.state.get()
        if st.get("config", {}).get("house_rules", {}).get("auto_xp_desperate", True) and actor and position == "Отчаянная":
            self.state.add_player_xp(actor, 1)
        if quality == "critical":
            self.state.add_crew_xp(1)

    def step(self, history: List[Dict[str, str]], user_input: str, log_dir: str | None = "data/logs") -> Dict[str, Any]:
        turns = [ChatTurn(**h) for h in history] + [ChatTurn(role="user", content=user_input)]
        raw = self.llm.chat(SYSTEM_PROMPT_RU, turns)
        intent, narration = self._extract_intent(raw)

        tool_result = None
        if intent and "intent" in intent:
            typ = intent["intent"]
            proposed = intent.get("proposed", {})
            if typ == "ask_for_action_roll":
                if not proposed.get("position") or not proposed.get("effect"):
                    inf = self._infer_position_effect(user_input)
                    if inf:
                        proposed.setdefault("position", inf.get("position"))
                        proposed.setdefault("effect", inf.get("effect"))
                actor = proposed.get("actor")
                action = proposed.get("action")
                dice = self._dice_from_actor_and_mods(actor, action, proposed)
                res = action_roll(int(dice))
                eff = proposed.get("effect", "Обычный")
                pos = proposed.get("position", None)
                target = proposed.get("target_clock", None)
                cons_suggest = None
                if pos and res["quality"] in ("partial","bad"):
                    cons_suggest = self.state.consequence_suggest(pos, res["quality"])
                # Fill target clock on success
                if res["quality"] in ("full", "critical", "partial") and target and isinstance(target, dict):
                    name = target.get("name")
                    if name:
                        segments = effect_to_segments(eff)
                        try:
                            self.state.fill_clock(name, segments)
                        except Exception:
                            segs = int(target.get("segments", 4))
                            self.state.upsert_clock(name, segs)
                            self.state.fill_clock(name, segments)
                # Side-effects: assist costs 1 stress to helper; group action: leader takes failures stress
                try:
                    if _truthy(proposed.get("assist")) and proposed.get("assist_actor"):
                        cur = self.state.get(); old = int(cur.get("players", {}).get(proposed.get("assist_actor"), {}).get("stress", 0)); self.state.set_stress(proposed.get("assist_actor"), old + 1)
                    if _truthy(proposed.get("group_action")) and proposed.get("leader"):
                        fails = int(proposed.get("group_failures", 0) or 0)
                        if fails>0:
                            cur = self.state.get(); old = int(cur.get("players", {}).get(proposed.get("leader"), {}).get("stress", 0)); self.state.set_stress(proposed.get("leader"), old + fails)
                except Exception:
                    pass
                # House rules
                self._apply_house_rep_heat(res["quality"])
                self._apply_house_xp(pos, actor, res["quality"])
                # Tool result & banner
                tool_result = {
                    "type": "action_roll", "dice": int(dice), **res,
                    "actor": actor, "action": action,
                    "position": pos, "effect": eff,
                    "consequences": cons_suggest or [],
                    "modifiers": {"setup": bool(_truthy(proposed.get("setup"))), "assist_actor": proposed.get("assist_actor"),
                        "assist": bool(_truthy(proposed.get("assist"))),
                        "push": bool(_truthy(proposed.get("push"))),
                        "bargain": bool(_truthy(proposed.get("bargain"))),
                        "bonus": int(proposed.get("bonus", 0) or 0),
                    }
                }
                self.state.set_last_roll({
                    "kind": "action",
                    "actor": actor, "action": action,
                    "position": pos, "effect": eff,
                    "dice": int(dice), "rolls": res["rolls"], "best": res["best"],
                    "quality": res["quality"], "crit": res["crit"],
                    "modifiers": tool_result["modifiers"],
                    "target_clock": proposed.get("target_clock") if isinstance(proposed.get("target_clock"), dict) else None,
                    "consequences": cons_suggest or []
                })

            elif typ == "resist_prompt":
                dice = int(proposed.get("dice_guess", 1))
                actor = proposed.get("actor")
                res = resistance_roll(dice)
                if actor:
                    try:
                        cur = self.state.get()
                        old = int(cur.get("players", {}).get(actor, {}).get("stress", 0))
                        self.state.set_stress(actor, old + int(res["stress_cost"]))
                    except Exception:
                        pass
                tool_result = {"type": "resistance", "dice": dice, **res, "actor": actor}
                self.state.set_last_roll({"kind": "resist", "actor": actor, "dice": dice, "rolls": res["rolls"], "best": res["best"], "stress_cost": res["stress_cost"]})

            elif typ == "fortune_roll":
                dice = int(proposed.get("dice_guess", 1))
                res = fortune_roll(dice)
                tool_result = {"type": "fortune", "dice": dice, **res}
                self.state.set_last_roll({"kind": "fortune", "dice": dice, "rolls": res["rolls"], "best": res["best"]})

            elif typ == "engagement":
                dice = int(proposed.get("dice_guess", 1))
                res = fortune_roll(dice)
                pos = "Отчаянная" if res["best"] <= 3 else ("Рискованная" if res["best"] <= 5 else "Контролируемая")
                tool_result = {"type": "engagement", "dice": dice, **res, "start_position": pos}
                self.state.set_last_roll({"kind": "engagement", "dice": dice, "rolls": res["rolls"], "best": res["best"], "start_position": pos})

            elif typ == "downtime":
                tool_result = {"type": "downtime_ack"}
                self.state.set_last_roll({"kind": "downtime"})

        # logging
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            path = os.path.join(log_dir, "chat.jsonl")
            with open(path, "a", encoding="utf-8") as f:
                rec = {
                    "history": [h for h in history],
                    "user": user_input,
                    "assistant_raw": raw,
                    "assistant_narration": narration,
                    "assistant_intent": intent,
                    "tool_result": tool_result,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        return {"raw": raw, "narration": narration, "intent": intent, "tool_result": tool_result}
