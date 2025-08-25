
from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn, os, json, csv, io, random, traceback

from .state import StateStore, DEFAULT_ACTIONS
from .gm_agent import GMAgent
from .tools import action_roll, resistance_roll, fortune_roll

app = FastAPI(title="BitD GM AI")

state = StateStore(path=os.getenv("BITD_STATE_PATH", "data/state.json"))
agent = GMAgent(state)

class ChatReq(BaseModel):
    history: List[Dict[str, str]] = []
    user: str

class ChatResp(BaseModel):
    narration: str
    intent: Dict[str, Any] | None
    tool_result: Dict[str, Any] | None
    raw: str

@app.post("/chat", response_model=ChatResp)
def chat(body: ChatReq):
    out = agent.step(body.history, body.user)
    return ChatResp(**out)

@app.get("/state")
def get_state():
    return state.get()

# ---------- Config & Rules ----------
class ConfigUpdate(BaseModel):
    path: List[str]
    value: Any

@app.post("/config/update")
def config_update(body: ConfigUpdate):
    state.set_config(body.path, body.value)
    return {"ok": True, "state": state.get()}

class Thresholds(BaseModel):
    player: Optional[int] = None
    crew: Optional[int] = None

@app.post("/rules/set_thresholds")
def rules_thresholds(body: Thresholds):
    state.set_thresholds(player=body.player, crew=body.crew)
    return {"ok": True, "state": state.get()}

class PresetBody(BaseModel):
    name: str

@app.post("/rules/use_preset")
def rules_use_preset(body: PresetBody):
    state.use_trigger_preset(body.name)
    return {"ok": True, "state": state.get()}

class ConsSuggest(BaseModel):
    position: str
    quality: str

@app.post("/rules/consequence_suggest")
def rules_consequence_suggest(body: ConsSuggest):
    return {"suggestions": state.consequence_suggest(body.position, body.quality)}

# ---------- Clocks & Meta ----------
class ClockCreate(BaseModel):
    name: str
    segments: int

class ClockFill(BaseModel):
    name: str
    n: int

@app.post("/clock/create")
def clock_create(body: ClockCreate):
    state.upsert_clock(body.name, body.segments)
    return {"ok": True, "state": state.get()}

@app.post("/clock/fill")
def clock_fill(body: ClockFill):
    state.fill_clock(body.name, body.n)
    return {"ok": True, "state": state.get()}

class MetaUpdate(BaseModel):
    heat: Optional[int] = None
    wanted: Optional[int] = None
    rep: Optional[int] = None
    coin: Optional[int] = None

@app.post("/state/update")
def update_meta(body: MetaUpdate):
    state.set_meta(heat=body.heat, wanted=body.wanted, rep=body.rep, coin=body.coin)
    return {"ok": True, "state": state.get()}

# ---------- Dice ----------
class DiceReq(BaseModel):
    dice: int

@app.post("/roll/action")
def roll_action(body: DiceReq):
    return action_roll(body.dice)

@app.post("/roll/resist")
def roll_resist(body: DiceReq):
    return resistance_roll(body.dice)

@app.post("/roll/fortune")
def roll_fortune(body: DiceReq):
    return fortune_roll(body.dice)

# GM helpers
class D6Req(BaseModel):
    dice: int

@app.post("/gm/d6")
def gm_d6(body: D6Req):
    rolls = [random.randint(1,6) for _ in range(max(1, int(body.dice)))]
    return {"rolls": rolls, "best": max(rolls) if rolls else None}

class Flashback(BaseModel):
    name: str
    stress_cost: int

@app.post("/gm/flashback")
def gm_flashback(body: Flashback):
    cur = state.get()
    old = int(cur.get("players", {}).get(body.name, {}).get("stress", 0))
    state.set_stress(body.name, old + int(body.stress_cost))
    return {"ok": True, "state": state.get()}

# ---------- Characters ----------
class PlayerCreate(BaseModel):
    name: str

class PlayerSetAction(BaseModel):
    name: str
    action: str
    rating: int

class PlayerStress(BaseModel):
    name: str
    stress: int

class PlayerTrauma(BaseModel):
    name: str
    label: str

class PlayerConsumePending(BaseModel):
    name: str
    label: str

@app.post("/player/upsert")
def player_upsert(body: PlayerCreate):
    state.upsert_player(body.name)
    return {"ok": True, "state": state.get(), "actions": DEFAULT_ACTIONS}

@app.post("/player/set_action")
def player_set_action(body: PlayerSetAction):
    state.set_action(body.name, body.action, body.rating)
    return {"ok": True, "state": state.get()}

@app.post("/player/set_stress")
def player_set_stress(body: PlayerStress):
    state.set_stress(body.name, body.stress)
    return {"ok": True, "state": state.get()}

@app.post("/player/add_trauma")
def player_add_trauma(body: PlayerTrauma):
    state.add_trauma(body.name, body.label)
    return {"ok": True, "state": state.get()}

@app.post("/player/consume_pending_trauma")
def player_consume_pending(body: PlayerConsumePending):
    state.consume_pending_trauma(body.name, body.label)
    return {"ok": True, "state": state.get()}

# Resistance that also applies stress directly
class ResistApply(BaseModel):
    name: str
    dice: int

@app.post("/roll/resist_apply")
def roll_resist_apply(body: ResistApply):
    res = resistance_roll(body.dice)
    try:
        cur = state.get()
        old = int(cur.get("players", {}).get(body.name, {}).get("stress", 0))
        state.set_stress(body.name, old + int(res["stress_cost"]))
    except Exception:
        pass
    return {"applied_to": body.name, **res, "state": state.get()}

# ---------- Crew ----------
class CrewUpdate(BaseModel):
    name: Optional[str] = None
    playbook: Optional[str] = None
    tier: Optional[int] = None
    hold: Optional[str] = None
    upgrades: Optional[Dict[str, Any]] = None

@app.post("/crew/update")
def crew_update(body: CrewUpdate):
    state.set_crew(name=body.name, playbook=body.playbook, tier=body.tier, hold=body.hold, upgrades=body.upgrades or None)
    return {"ok": True, "state": state.get()}

# ---------- Campaigns ----------
class CampaignCreate(BaseModel):
    name: str

class CampaignSwitch(BaseModel):
    name: str

@app.post("/campaign/create")
def campaign_create(body: CampaignCreate):
    state.create_campaign(body.name)
    return {"ok": True, "state": state.get(), "campaigns": state.list_campaigns()}

@app.post("/campaign/switch")
def campaign_switch(body: CampaignSwitch):
    state.switch_campaign(body.name)
    return {"ok": True, "state": state.get(), "campaigns": state.list_campaigns()}

@app.get("/campaign/list")
def campaign_list():
    return {"campaigns": state.list_campaigns(), "state": state.get()}

# ---------- Factions ----------
class FacUpsert(BaseModel):
    name: str

class FacStatus(BaseModel):
    name: str
    status: int

class FacClockCreate(BaseModel):
    name: str
    clock: str
    segments: int

class FacClockFill(BaseModel):
    name: str
    clock: str
    n: int

@app.post("/faction/upsert")
def faction_upsert(body: FacUpsert):
    state.faction_upsert(body.name)
    return {"ok": True, "state": state.get()}

@app.post("/faction/set_status")
def faction_set_status(body: FacStatus):
    state.faction_set_status(body.name, body.status)
    return {"ok": True, "state": state.get()}

@app.post("/faction/clock_create")
def faction_clock_create(body: FacClockCreate):
    state.faction_clock_create(body.name, body.clock, body.segments)
    return {"ok": True, "state": state.get()}

@app.post("/faction/clock_fill")
def faction_clock_fill(body: FacClockFill):
    state.faction_clock_fill(body.name, body.clock, body.n)
    return {"ok": True, "state": state.get()}

# ---------- Logs export ----------
@app.get("/logs/export_json")
def logs_export_json():
    path = "data/logs/chat.jsonl"
    arr = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    arr.append(json.loads(line))
    except FileNotFoundError:
        pass
    return {"count": len(arr), "records": arr}

@app.get("/logs/export_csv")
def logs_export_csv():
    path = "data/logs/chat.jsonl"
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user","assistant_narration","intent_intent","intent_actor","intent_action","tool_type","rolls","best","quality"])
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                intent = rec.get("assistant_intent") or {}
                proposed = intent.get("proposed") or {}
                tool = rec.get("tool_result") or {}
                writer.writerow([
                    rec.get("user",""),
                    rec.get("assistant_narration",""),
                    intent.get("intent",""),
                    proposed.get("actor",""),
                    proposed.get("action",""),
                    tool.get("type",""),
                    json.dumps(tool.get("rolls",[]), ensure_ascii=False),
                    tool.get("best",""),
                    tool.get("quality","")
                ])
    except FileNotFoundError:
        pass
    return {"csv": output.getvalue()}


# ---------- Consequences / Harms / XP ----------
class HarmAdd(BaseModel):
    name: str
    level: int
    label: str
    kind: str | None = None

class HarmClear(BaseModel):
    name: str
    idx: int

@app.post("/player/add_harm")
def player_add_harm(body: HarmAdd):
    state.add_harm(body.name, body.level, body.label, body.kind)
    return {"ok": True, "state": state.get()}

@app.get("/player/list_harms")
def player_list_harms(name: str):
    return {"harms": state.list_harms(name)}

@app.post("/player/clear_harm")
def player_clear_harm(body: HarmClear):
    state.clear_harm(body.name, body.idx)
    return {"ok": True, "state": state.get()}

class ConseqUpdate(BaseModel):
    position: str        # Контролируемая/Рискованная/Отчаянная
    key: str             # partial|bad
    lines: list[str]     # список строк

@app.post("/rules/update_consequences")
def rules_update_consequences(body: ConseqUpdate):
    cur = state.get()
    cons = cur.setdefault("config", {}).setdefault("rules", {}).setdefault("consequences", {})
    cons.setdefault(body.position, {})
    cons[body.position][body.key] = body.lines
    state.save_current(cur)
    return {"ok": True, "state": state.get()}

class XPAward(BaseModel):
    name: str
    n: int

@app.post("/xp/award")
def xp_award(body: XPAward):
    state.add_player_xp(body.name, body.n)
    return {"ok": True, "state": state.get()}

class CrewXPAward(BaseModel):
    n: int

@app.post("/xp/crew_award")
def xp_crew_award(body: CrewXPAward):
    state.add_crew_xp(body.n)
    return {"ok": True, "state": state.get()}

class ApplySuggested(BaseModel):
    suggestion: str
    actor: str | None = None
    clock_name: str | None = None
    default_segments: int | None = None

@app.post("/gm/apply_suggested")
def gm_apply_suggested(body: ApplySuggested):
    s = body.suggestion
    try:
        # harm N
        m = re.search(r"[Hh]arm\s*(\d)", s) or re.search(r"harm\s*(\d)", s)
        if m and body.actor:
            level = int(m.group(1))
            label = re.sub(r"\(.*?harm.*?\)", "", s, flags=re.IGNORECASE).strip(" -–:")
            state.add_harm(body.actor, level, label or f"Harm {level}")
            return {"applied": "harm", "level": level, "actor": body.actor, "state": state.get()}
        # Heat +N
        m = re.search(r"[Hh]eat\s*\+\s*(\d+)", s)
        if m:
            n = int(m.group(1))
            cur = state.get()
            state.set_meta(heat=cur.get("heat",0)+n)
            return {"applied": "heat", "delta": n, "state": state.get()}
        # Clock +N
        m = re.search(r"(час|clock)[^\d+]*\+\s*(\d+)", s, re.IGNORECASE) or re.search(r":\s*(\d+)$", s)
        if m and (body.clock_name or body.default_segments):
            if body.clock_name:
                state.fill_clock(body.clock_name, int(m.group(2) if m.lastindex else 1))
                return {"applied": "clock_fill", "clock": body.clock_name, "delta": int(m.group(2) if m.lastindex else 1), "state": state.get()}
            else:
                # create default and fill
                nm = "Сцена: последствие"
                state.upsert_clock(nm, int(body.default_segments or 4))
                state.fill_clock(nm, int(m.group(2) if m.lastindex else 1))
                return {"applied": "clock_fill", "clock": nm, "delta": int(m.group(2) if m.lastindex else 1), "state": state.get()}
        # Complication → создать короткий час, заполнить +1, если не указано иное
        if re.search(r"компликац|complicat", s, re.IGNORECASE):
            nm = body.clock_name or ("Компликация: " + s[:32])
            state.upsert_clock(nm, int(body.default_segments or 4))
            # если не нашли +N, заполним +1
            mfill = re.search(r"\+\s*(\d+)", s)
            fill = int(mfill.group(1)) if mfill else 1
            state.fill_clock(nm, fill)
            return {"applied": "complication_clock", "clock": nm, "delta": fill, "state": state.get()}
        # Complication/noop
        return {"applied": "noop", "note": "Не удалось распознать/требуются параметры (actor/clock) для применения.", "state": state.get()}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}

# ---------- Export PDF (requires reportlab) ----------
@app.get("/export/pdf")
def export_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as rcanvas
    except Exception as e:
        return {"ok": False, "error": f"reportlab not available: {e}"}
    try:
        cur = state.get()
        path = "exports/cards.pdf"
        os.makedirs("exports", exist_ok=True)
        c = rcanvas.Canvas(path, pagesize=A4)
        w, h = A4
        y = h - 20*mm
        c.setFont("Helvetica-Bold", 16); c.drawString(20*mm, y, f"Crew: {cur.get('crew',{}).get('name','—')}")
        y -= 10*mm
        c.setFont("Helvetica", 12)
        for name, p in cur.get("players", {}).items():
            if y < 40*mm:
                c.showPage(); y = h - 20*mm
            harms = ", ".join([f"{x.get('label','')} (H{x.get('level',1)})" for x in p.get("harms",[])])
            trauma = ", ".join(p.get("trauma", []))
            c.drawString(20*mm, y, f"{name} — XP {p.get('xp',0)} (adv {p.get('advances',0)})")
            y -= 6*mm
            c.drawString(25*mm, y, f"Stress {p.get('stress',0)}/9 | Trauma: {trauma or '—'} | Harms: {harms or '—'}")
            y -= 10*mm
        c.showPage(); c.save()
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------- Scene suggestions ----------
class AddSuggestion(BaseModel):
    line: str

@app.post("/gm/add_suggestion")
def gm_add_suggestion(body: AddSuggestion):
    state.add_last_roll_suggestion(body.line)
    return {"ok": True, "state": state.get()}


# ---------- Scene consequence presets ----------
class ScenePresetSave(BaseModel):
    name: str

class ScenePresetApply(BaseModel):
    name: str

@app.post("/rules/save_scene_preset")
def rules_save_scene_preset(body: ScenePresetSave):
    state.save_scene_consequence_preset(body.name)
    return {"ok": True, "presets": state.list_scene_consequence_presets()}

@app.post("/rules/apply_scene_preset")
def rules_apply_scene_preset(body: ScenePresetApply):
    state.apply_scene_consequence_preset(body.name)
    return {"ok": True, "state": state.get()}

@app.get("/rules/list_scene_presets")
def rules_list_scene_presets():
    return {"presets": state.list_scene_consequence_presets()}

# ---------- Import/Export state ----------


@app.get("/export")
def export_state():
    return state.export_state()

class ImportBody(BaseModel):
    payload: Dict[str, Any]

@app.post("/import")
def import_state(body: ImportBody):
    state.import_state(body.payload)
    return {"ok": True, "state": state.get()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
