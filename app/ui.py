
import gradio as gr
import requests, os, json, math

API = os.getenv("GM_API", "http://127.0.0.1:8000")

history: list[dict[str,str]] = []

def get_state():
    r = requests.get(f"{API}/state", timeout=30)
    r.raise_for_status()
    return r.json()

def donut_svg(name, filled, total, size=96, stroke=12):
    radius = (size - stroke) / 2
    center = size/2
    circumference = 2 * math.pi * radius
    progress = (filled / max(1,total)) * circumference
    remaining = circumference - progress
    svg = f"""
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="#e5e7eb" stroke-width="{stroke}" />
  <circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="#10b981" stroke-width="{stroke}"
    stroke-dasharray="{progress} {remaining}" transform="rotate(-90 {center} {center})" stroke-linecap="round"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-size="14" font-family="Inter,Arial">{filled}/{total}</text>
</svg>
"""
    label = f'<div style="text-align:center;font-weight:600;margin-top:4px">{name}</div>'
    return f'<div style="display:inline-block;margin:6px">{svg}{label}</div>'

def render_clocks_svg(s):
    html = ""
    for c in s.get("clocks", []):
        html += donut_svg(c["name"], int(c["filled"]), int(c["segments"]))
    if not html:
        html = "<i>Часов пока нет.</i>"
    return html

def player_card(name, data, th_player=8):
    stress = int(data.get("stress", 0))
    pending = int(data.get("pending_trauma", 0))
    xp = int(data.get("xp", 0))
    adv = int(data.get("advances", 0))
    trauma = ", ".join(data.get("trauma", [])) or "—"
    harms = ", ".join([f"{h.get('label','')} (H{h.get('level',1)})" for h in data.get("harms", [])]) or "—"
    actions = data.get("actions", {})
    top = sorted(actions.items(), key=lambda kv: kv[1], reverse=True)[:4]
    top_txt = ", ".join([f"{k}:{v}" for k,v in top if v>0]) or "нет точек"
    stress_boxes = "".join(["■" if i < stress else "□" for i in range(9)])
    pend_txt = f" (+{pending} в ожидании)" if pending>0 else ""
    xp_prog = f"{xp}/{th_player} (appr: {adv})"
    return f"""
<div style='border:1px solid #e5e7eb;border-radius:12px;padding:10px;margin:6px;display:inline-block;min-width:220px'>
  <div style='font-weight:700'>{name} <span style="background:#eef6ff;border:1px solid #bfdbfe;padding:0 6px;border-radius:8px;font-size:12px">XP {xp_prog}</span></div>
  <div>Стресс: {stress_boxes}{pend_txt}</div>
  <div>Травмы: {trauma}</div>
  <div>Раны: {harms}</div>
  <div>Топ действия: {top_txt}</div>
</div>
"""

def render_players_cards(s):
    th_player = int(s.get("config", {}).get("house_rules", {}).get("advance_threshold_player", 8))
    players = s.get("players", {})
    if not players:
        return "<i>Нет персонажей.</i>"
    return "".join([player_card(n, d, th_player) for n,d in players.items()])

def crew_card(s):
    crew = s.get("crew", {})
    th = int(s.get("config", {}).get("house_rules", {}).get("advance_threshold_crew", 8))
    name = crew.get("name","—"); play = crew.get("playbook","—"); tier = crew.get("tier",0); hold = crew.get("hold","—"); xp = crew.get("xp", 0); adv = crew.get("advances", 0)
    return f"""
<div style='border:1px solid #e5e7eb;border-radius:12px;padding:10px;margin:6px;display:inline-block;min-width:260px;background:#fafafa'>
  <div style='font-weight:700'>Crew: {name} <span style="background:#ecfdf5;border:1px solid #bbf7d0;padding:0 6px;border-radius:8px;font-size:12px">XP {xp}/{th} (appr: {adv})</span></div>
  <div>Playbook: {play}</div>
  <div>Tier: {tier} / Hold: {hold}</div>
</div>
"""

def last_roll_banner(s):
    lr = s.get("last_roll")
    if not lr: return ""
    kind = lr.get("kind")
    if kind == "action":
        mods = lr.get("modifiers", {})
        mods_txt = []
        for k in ["assist","push","bargain"]:
            if mods.get(k): mods_txt.append("+"+k)
        if mods.get("bonus",0):
            mods_txt.append(f"+{mods.get('bonus')}b")
        mtxt = (" [" + ", ".join(mods_txt) + "]") if mods_txt else ""
        cons = lr.get("consequences") or []
        cons_txt = ("\n\n**Предложенные последствия:**\n- " + "\n- ".join(cons)) if cons else ""
        return f"**Последний бросок:** {lr.get('actor') or '—'} / {lr.get('action') or '—'} — {lr.get('dice')}d{mtxt} → {lr.get('rolls')} (лучший {lr.get('best')}) | качество: {lr.get('quality')} | позиция: {lr.get('position') or '—'} | эффект: {lr.get('effect') or '—'}{cons_txt}"
    elif kind == "resist":
        return f"**Сопротивление:** {lr.get('actor') or '—'} — {lr.get('dice')}d → {lr.get('rolls')} (лучший {lr.get('best')}) | стресс: +{lr.get('stress_cost')}"
    elif kind == "engagement":
        return f"**Engagement:** {lr.get('dice')}d → {lr.get('rolls')} (лучший {lr.get('best')}) | стартовая позиция: {lr.get('start_position')}"
    elif kind == "fortune":
        return f"**Fortune:** {lr.get('dice')}d → {lr.get('rolls')} (лучший {lr.get('best')})"
    else:
        return f"**Система:** {kind}"

def render_factions(s):
    def donut(name, filled, segments): return donut_svg(name, filled, segments, size=72, stroke=10)
    facs = s.get("factions", {})
    if not facs: return "<i>Фракции не заведены.</i>"
    html = ""
    for name, data in facs.items():
        st = int(data.get("status", 0))
        clocks_html = "".join(donut(c["name"], int(c["filled"]), int(c["segments"])) for c in data.get("clocks", []))
        html += f"""
<div style='border:1px solid #e5e7eb;border-radius:12px;padding:10px;margin:6px;display:inline-block;min-width:240px'>
  <div style='font-weight:700'>{name} <span style="background:#fff7ed;border:1px solid #fed7aa;padding:0 6px;border-radius:8px;font-size:12px">Статус: {st}</span></div>
  <div>{clocks_html or '<i>Часов нет</i>'}</div>
</div>
"""
    return html

def refresh_all():
    s = get_state()
    meta = f"**Кампания:** {s.get('current_campaign')}  |  **Coin:** {s.get('coin',0)} | **Rep:** {s.get('rep',0)} | **Heat:** {s.get('heat',0)} | **Wanted:** {s.get('wanted',0)}"
    clocks_html = render_clocks_svg(s)
    players_html = render_players_cards(s) + crew_card(s)
    factions_html = render_factions(s)
    cfg = s.get("config", {}).get("house_rules", {})
    cfg_auto = bool(cfg.get("auto_rep_heat", True))
    cfg_auto_xp = bool(cfg.get("auto_xp_desperate", True))
    presets = s.get("config", {}).get("rules", {}).get("trigger_presets", ["Стандарт"])
    banner = last_roll_banner(s)
    return meta, clocks_html, players_html, factions_html, json.dumps(s, ensure_ascii=False, indent=2), cfg_auto, cfg_auto_xp, presets, banner

def chat(user_text: str):
    global history
    payload = {"history": history, "user": user_text}
    r = requests.post(f"{API}/chat", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": data["narration"]})
    blocks = []
    if data.get("intent"):
        blocks.append("**INTENT:**\n```json\n" + json.dumps(data["intent"], ensure_ascii=False, indent=2) + "\n```");
    if data.get("tool_result"):
        blocks.append("**TOOL RESULT:**\n```json\n" + json.dumps(data["tool_result"], ensure_ascii=False, indent=2) + "\n```");
    pretty = data["narration"] + ("\n\n" + "\n\n".join(blocks) if blocks else "")
    meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, presets, banner = refresh_all()
    return history, pretty, meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, gr.Dropdown.update(choices=presets), banner

# --- API helpers ---
def create_clock(name, segments): requests.post(f"{API}/clock/create", json={"name": name, "segments": int(segments)}, timeout=30).raise_for_status(); return refresh_all()
def fill_clock(name, n): requests.post(f"{API}/clock/fill", json={"name": name, "n": int(n)}, timeout=30).raise_for_status(); return refresh_all()
def update_meta(coin, rep, heat, wanted):
    requests.post(f"{API}/state/update", json={"coin": int(coin), "rep": int(rep), "heat": int(heat), "wanted": int(wanted)}, timeout=30).raise_for_status()
    return refresh_all()

def player_upsert(name): requests.post(f"{API}/player/upsert", json={"name": name}, timeout=30).raise_for_status(); return refresh_all()
def player_set_action(name, action, rating): requests.post(f"{API}/player/set_action", json={"name": name, "action": action, "rating": int(rating)}, timeout=30).raise_for_status(); return refresh_all()
def player_set_stress(name, stress): requests.post(f"{API}/player/set_stress", json={"name": name, "stress": int(stress)}, timeout=30).raise_for_status(); return refresh_all()
def player_resist(name, dice):
    r = requests.post(f"{API}/roll/resist_apply", json={"name": name, "dice": int(dice)}, timeout=30)
    r.raise_for_status()
    out = r.json()
    meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, presets, banner = refresh_all()
    details = "```json\n" + json.dumps(out, ensure_ascii=False, indent=2) + "\n```"
    return details, meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, gr.Dropdown.update(choices=presets), banner

def crew_update(name, playbook, tier, hold):
    payload = {"name": name or None, "playbook": playbook or None, "tier": int(tier) if tier is not None else None, "hold": hold or None}
    r = requests.post(f"{API}/crew/update", json=payload, timeout=30); r.raise_for_status()
    return refresh_all()

def cfg_toggle_auto(flag: bool):
    r = requests.post(f"{API}/config/update", json={"path": ["house_rules","auto_rep_heat"], "value": bool(flag)}, timeout=30); r.raise_for_status()
    return refresh_all()

def cfg_toggle_auto_xp(flag: bool):
    r = requests.post(f"{API}/config/update", json={"path": ["house_rules","auto_xp_desperate"], "value": bool(flag)}, timeout=30); r.raise_for_status()
    return refresh_all()

def set_thresholds(player_th, crew_th):
    r = requests.post(f"{API}/rules/set_thresholds", json={"player": int(player_th), "crew": int(crew_th)}, timeout=30); r.raise_for_status()
    return refresh_all()

def use_preset(preset):
    r = requests.post(f"{API}/rules/use_preset", json={"name": preset}, timeout=30); r.raise_for_status()
    return refresh_all()

def gm_d6(n):
    r = requests.post(f"{API}/gm/d6", json={"dice": int(n)}, timeout=30); r.raise_for_status()
    return "```json\n" + json.dumps(r.json(), ensure_ascii=False, indent=2) + "\n```"

def gm_fortune(n):
    r = requests.post(f"{API}/roll/fortune", json={"dice": int(n)}, timeout=30); r.raise_for_status()
    return "```json\n" + json.dumps(r.json(), ensure_ascii=False, indent=2) + "\n```"

def gm_flashback(name, cost):
    r = requests.post(f"{API}/gm/flashback", json={"name": name, "stress_cost": int(cost)}, timeout=30); r.raise_for_status()
    return refresh_all()

def fac_upsert(name):
    r = requests.post(f"{API}/faction/upsert", json={"name": name}, timeout=30); r.raise_for_status()
    return refresh_all()

def fac_set_status(name, status):
    r = requests.post(f"{API}/faction/set_status", json={"name": name, "status": int(status)}, timeout=30); r.raise_for_status()
    return refresh_all()

def fac_clock_create(name, clock, segments):
    r = requests.post(f"{API}/faction/clock_create", json={"name": name, "clock": clock, "segments": int(segments)}, timeout=30); r.raise_for_status()
    return refresh_all()

def fac_clock_fill(name, clock, n):
    r = requests.post(f"{API}/faction/clock_fill", json={"name": name, "clock": clock, "n": int(n)}, timeout=30); r.raise_for_status()
    return refresh_all()

def export_logs_json():
    r = requests.get(f"{API}/logs/export_json", timeout=30); r.raise_for_status()
    data = r.json()
    return json.dumps(data, ensure_ascii=False, indent=2)

def export_logs_csv():
    r = requests.get(f"{API}/logs/export_csv", timeout=30); r.raise_for_status()
    data = r.json()
    return data.get("csv","")

def do_export():
    r = requests.get(f"{API}/export", timeout=30); r.raise_for_status()
    return json.dumps(r.json(), ensure_ascii=False, indent=2)

def do_import(state_json_text):
    import gradio as gr
    try:
        payload = json.loads(state_json_text)
    except Exception as e:
        return gr.update(value="Ошибка парсинга JSON: "+str(e))
    r = requests.post(f"{API}/import", json={"payload": payload}, timeout=30); r.raise_for_status()
    return refresh_all()

with gr.Blocks(title="BitD GM AI — правила, пресеты, мастер-панель") as demo:
    gr.Markdown("# BitD GM AI — Consequences, Presets, GM Panel")
    banner_box = gr.Markdown()

    # Quick actions under banner
    gr.Markdown("### Быстро применить последствие")
    with gr.Row():
        btn_apply_0 = gr.Button("Применить #1")
        btn_apply_1 = gr.Button("Применить #2")
        btn_apply_2 = gr.Button("Применить #3")
        btn_apply_3 = gr.Button("Применить #4")
    with gr.Row():
        btn_apply_4 = gr.Button("Применить #5")
        btn_apply_5 = gr.Button("Применить #6")
        btn_apply_6 = gr.Button("Применить #7")
        btn_apply_7 = gr.Button("Применить #8")
    sugg_dd = gr.Dropdown(choices=get_last_suggestions(), label="Предложенные последствия (из баннера)")
    q_actor = gr.Textbox(label="Actor (по умолчанию авто)")
    q_clock = gr.Textbox(label="Clock (если надо)")
    q_seg = gr.Number(label="Если Clock пуст — создать часов сегментов", value=4, precision=0)
    btn_q_apply = gr.Button("Применить выбранное")

    gr.Markdown("Добавить своё последствие в баннер текущей сцены")
    new_sugg = gr.Textbox(label="Текст последствия")
    btn_add_sugg = gr.Button("Добавить")


    meta_box = gr.Markdown()
    clocks_box = gr.HTML()
    players_box = gr.HTML()
    factions_box = gr.HTML()
    state_json = gr.Code(label="Текущее состояние (JSON)", language="json", interactive=False)

    cfg_auto = gr.Checkbox(value=True, label="Дом-правило: авто REP/HEAT")
    cfg_auto_xp = gr.Checkbox(value=True, label="Дом-правило: авто XP за Отчаянную")
    th_player = gr.Number(label="Порог апгрейда персонажа", value=8, precision=0)
    th_crew = gr.Number(label="Порог апгрейда Crew", value=8, precision=0)
    btn_set_th = gr.Button("Сохранить пороги")

    presets_dd = gr.Dropdown(choices=["Стандарт"], value="Стандарт", label="Пресет триггеров сцены")
    btn_use_preset = gr.Button("Применить пресет")

    chatbot = gr.Chatbot(height=260, label="Диалог")
    msg = gr.Textbox(placeholder="Опишите действие/сцену… (actor/action/assist/push/bargain/bonus приветствуются)", label="Сообщение")
    send = gr.Button("Отправить")

    with gr.Accordion("GM Панель", open=False):
        d6n = gr.Number(label="Простой d6 (сколько кубов)", value=1, precision=0)
        btn_d6 = gr.Button("Бросить d6")
        d6_out = gr.Markdown()
        forn = gr.Number(label="Fortune (сколько кубов)", value=2, precision=0)
        btn_for = gr.Button("Fortune Roll")
        for_out = gr.Markdown()
        fb_name = gr.Textbox(label="Flashback — имя персонажа")
        fb_cost = gr.Number(label="Стоимость стресса (0/1/2)", value=1, precision=0)
        btn_fb = gr.Button("Применить Flashback")
        # quick fill clock
        q_clock = gr.Textbox(label="Быстро заполнить час — имя")
        q_fill = gr.Number(label="Сегментов", value=1, precision=0)
        btn_qfill = gr.Button("Заполнить")

    
    with gr.Accordion("Последствия (редактор) и Применение", open=False):
        gr.Markdown("#### Пресеты списка последствий (сцены)")
        pr_name = gr.Textbox(label="Название пресета")
        btn_pr_save = gr.Button("Сохранить текущие предложения как пресет")
        pr_list = gr.Textbox(label="Имеющиеся пресеты", interactive=False)
        pr_apply = gr.Dropdown(choices=list_scene_presets(), label="Применить пресет к текущей сцене")
        btn_pr_apply = gr.Button("Применить выбранный пресет")
        with gr.Row():
            pos = gr.Dropdown(choices=["Контролируемая","Рискованная","Отчаянная"], value="Рискованная", label="Позиция")
            qual = gr.Dropdown(choices=["partial","bad"], value="partial", label="Ключ")
        cons_text = gr.Textbox(lines=6, label="Список последствий (по одному на строку)")
        btn_load_cons = gr.Button("Загрузить из состояния")
        btn_save_cons = gr.Button("Сохранить")
        gr.Markdown("### Применить предложенное последствие из баннера")
        sel = gr.Textbox(label="Текст выбранного последствия (скопируйте из баннера)")
        sel_actor = gr.Textbox(label="Actor (для harm)")
        sel_clock = gr.Textbox(label="Clock name (если указано +N к часам)")
        sel_default = gr.Number(label="Если clock пуст — создать часов сегментов", value=4, precision=0)
        btn_apply = gr.Button("Применить последствие")
        apply_out = gr.Code(label="Результат применения", language="json")
    with gr.Accordion("XP быстрые кнопки", open=False):
        pl_choice = gr.Dropdown(choices=list_players(), label="Кому выдать XP")
        xp_n = gr.Number(label="Сколько XP (+/-)", value=1, precision=0)
        btn_xp = gr.Button("Выдать игроку XP")
        btn_cxp = gr.Button("Выдать Crew XP +1")
    with gr.Accordion("Экспорт в PDF", open=False):
        btn_pdf = gr.Button("Сгенерировать cards.pdf (reportlab)")
        pdf_out = gr.Markdown()
    
    with gr.Accordion("Раны (harms)", open=False):
        h_player = gr.Textbox(label="Игрок")
        h_level = gr.Dropdown(choices=["1","2","3"], value="1", label="Уровень")
        h_kind = gr.Dropdown(choices=["generic","physical","mental"], value="generic", label="Тип")
        h_label = gr.Textbox(label="Метка/описание")
        btn_h_add = gr.Button("Добавить рану")
        h_rm_idx = gr.Number(label="Удалить рану — индекс (0..)", value=0, precision=0)
        btn_h_rm = gr.Button("Удалить рану")
    with gr.Accordion("Часы и мета", open=False):
        name = gr.Textbox(label="Название часа")
        segs = gr.Number(label="Сегменты", value=4, precision=0)
        btn_create = gr.Button("Создать/обновить")
        fill_name = gr.Textbox(label="Какой час заполнить")
        fill_n = gr.Number(label="Сколько сегментов", value=1, precision=0)
        btn_fill = gr.Button("Заполнить")
        coin = gr.Number(label="Coin", value=2, precision=0)
        rep = gr.Number(label="Rep", value=0, precision=0)
        heat = gr.Number(label="Heat", value=0, precision=0)
        wanted = gr.Number(label="Wanted", value=0, precision=0)
        btn_meta = gr.Button("Обновить мету")

    with gr.Accordion("Фракции", open=False):
        fac_name = gr.Textbox(label="Название фракции")
        btn_fac = gr.Button("Создать/открыть фракцию")
        fac_status = gr.Number(label="Статус (-3..+3)", value=0, precision=0)
        btn_fac_status = gr.Button("Сохранить статус")
        fac_clock = gr.Textbox(label="Имя часов фракции")
        fac_segs = gr.Number(label="Сегменты", value=4, precision=0)
        btn_fac_clock_create = gr.Button("Создать/обновить часы")
        fac_fill_n = gr.Number(label="Заполнить сегментов", value=1, precision=0)
        btn_fac_clock_fill = gr.Button("Заполнить часы")

    with gr.Accordion("Импорт-Экспорт / Логи", open=False):
        btn_export = gr.Button("Экспортировать состояние в JSON")
        import_text = gr.Code(label="Вставьте JSON и нажмите Импорт", language="json")
        btn_import = gr.Button("Импортировать JSON")
        btn_logs_json = gr.Button("Экспорт логов (JSON)")
        logs_json = gr.Code(label="Логи (JSON)", language="json")
        btn_logs_csv = gr.Button("Экспорт логов (CSV)")
        logs_csv = gr.Code(label="Логи (CSV)", language="csv")

    # wiring
    send.click(chat, inputs=[msg], outputs=[chatbot, chatbot, meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    cfg_auto.change(cfg_toggle_auto, inputs=[cfg_auto], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    cfg_auto_xp.change(cfg_toggle_auto_xp, inputs=[cfg_auto_xp], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_set_th.click(set_thresholds, inputs=[th_player, th_crew], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_use_preset.click(use_preset, inputs=[presets_dd], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_d6.click(gm_d6, inputs=[d6n], outputs=[d6_out])
    btn_for.click(gm_fortune, inputs=[forn], outputs=[for_out])
    btn_fb.click(gm_flashback, inputs=[fb_name, fb_cost], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_qfill.click(fill_clock, inputs=[q_clock, q_fill], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_create.click(create_clock, inputs=[name, segs], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_fill.click(fill_clock, inputs=[fill_name, fill_n], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_meta.click(update_meta, inputs=[coin, rep, heat, wanted], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_fac.click(fac_upsert, inputs=[fac_name], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_fac_status.click(fac_set_status, inputs=[fac_name, fac_status], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_fac_clock_create.click(fac_clock_create, inputs=[fac_name, fac_clock, fac_segs], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_fac_clock_fill.click(fac_clock_fill, inputs=[fac_name, fac_clock, fac_fill_n], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_export.click(do_export, outputs=[import_text])
    btn_import.click(do_import, inputs=[import_text], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_logs_json.click(export_logs_json, outputs=[logs_json])
    btn_logs_csv.click(export_logs_csv, outputs=[logs_csv])

    meta, clocks_html, players_html, factions_html, state_json_text, cfg_flag, cfg_xp_flag, presets, banner = refresh_all()
    meta_box.value = meta
    clocks_box.value = clocks_html
    players_box.value = players_html
    factions_box.value = factions_html
    state_json.value = state_json_text
    cfg_auto.value = cfg_flag
    cfg_auto_xp.value = cfg_xp_flag
    presets_dd.choices = presets
    presets_dd.value = presets[0] if presets else "Стандарт"

# ----- Consequences editor & applier -----
def load_consequences(position, key):
    s = get_state()
    cons = s.get("config", {}).get("rules", {}).get("consequences", {})
    lines = cons.get(position, {}).get(key, [])
    return "\n".join(lines)

def save_consequences(position, key, text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    r = requests.post(f"{API}/rules/update_consequences", json={"position": position, "key": key, "lines": lines}, timeout=30); r.raise_for_status()
    return "Сохранено."

def apply_suggested(selected_text, actor, clock, default_segments):
    r = requests.post(f"{API}/gm/apply_suggested", json={"suggestion": selected_text, "actor": actor or None, "clock_name": clock or None, "default_segments": int(default_segments) if default_segments else None}, timeout=30); r.raise_for_status()
    out = r.json()
    meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, presets, banner = refresh_all()
    return json.dumps(out, ensure_ascii=False, indent=2), meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, gr.Dropdown.update(choices=presets), banner

# ----- XP quick award -----
def list_players():
    s = get_state()
    return list(s.get("players", {}).keys())

def xp_award(name, n):
    r = requests.post(f"{API}/xp/award", json={"name": name, "n": int(n)}, timeout=30); r.raise_for_status()
    return refresh_all()

def crew_xp_award(n):
    r = requests.post(f"{API}/xp/crew_award", json={"n": int(n)}, timeout=30); r.raise_for_status()
    return refresh_all()

# ----- PDF export -----
def export_pdf():
    r = requests.get(f"{API}/export/pdf", timeout=60); r.raise_for_status()
    return "```json\n" + json.dumps(r.json(), ensure_ascii=False, indent=2) + "\n```"

    btn_load_cons.click(load_consequences, inputs=[pos, qual], outputs=[cons_text])
    btn_save_cons.click(save_consequences, inputs=[pos, qual, cons_text], outputs=[gr.Markdown()])
    btn_apply.click(apply_suggested, inputs=[sel, sel_actor, sel_clock, sel_default], outputs=[apply_out, meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_xp.click(xp_award, inputs=[pl_choice, xp_n], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_cxp.click(crew_xp_award, inputs=[gr.Number.update(value=1)], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_pdf.click(export_pdf, outputs=[pdf_out])
    

def get_last_suggestions():
    s = get_state()
    lr = s.get("last_roll") or {}
    return lr.get("consequences", [])

def add_scene_suggestion(line):
    r = requests.post(f"{API}/gm/add_suggestion", json={"line": line}, timeout=30); r.raise_for_status()
    meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, presets, banner = refresh_all()
    return meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, gr.Dropdown.update(choices=get_last_suggestions()), banner

    btn_q_apply.click(apply_suggested, inputs=[sugg_dd, q_actor, q_clock, q_seg], outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_add_sugg.click(add_scene_suggestion, inputs=[new_sugg], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, sugg_dd, banner_box])

def add_harm_ui(name, level, label, kind):
    r = requests.post(f"{API}/player/add_harm", json={"name": name, "level": int(level), "label": label, "kind": (kind or None)}, timeout=30); r.raise_for_status()
    return refresh_all()

def clear_harm_ui(name, idx):
    r = requests.post(f"{API}/player/clear_harm", json={"name": name, "idx": int(idx)}, timeout=30); r.raise_for_status()
    return refresh_all()

def list_scene_presets():
    r = requests.get(f"{API}/rules/list_scene_presets", timeout=30); r.raise_for_status()
    return r.json().get("presets", [])

def save_scene_preset(name):
    r = requests.post(f"{API}/rules/save_scene_preset", json={"name": name}, timeout=30); r.raise_for_status()
    return ", ".join(r.json().get("presets", []))

def apply_scene_preset(name):
    r = requests.post(f"{API}/rules/apply_scene_preset", json={"name": name}, timeout=30); r.raise_for_status()
    meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, presets, banner = refresh_all()
    return meta, clocks_html, players_html, factions_html, state_json, cfg_auto, cfg_auto_xp, gr.Dropdown.update(choices=presets), banner

def quick_apply_idx(idx):
    s = get_state()
    sugg = (s.get("last_roll") or {}).get("consequences", []) or []
    if 0 <= idx < len(sugg):
        actor = (s.get("last_roll") or {}).get("actor")
        tclock = (s.get("last_roll") or {}).get("target_clock") or {}
        clock_name = tclock.get("name")
        return apply_suggested(sugg[idx], actor or "", clock_name or "", 4)
    else:
        return "{}", *refresh_all()

    btn_h_add.click(add_harm_ui, inputs=[h_player, h_level, h_label, h_kind], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_h_rm.click(clear_harm_ui, inputs=[h_player, h_rm_idx], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_pr_save.click(save_scene_preset, inputs=[pr_name], outputs=[pr_list])
    btn_pr_apply.click(apply_scene_preset, inputs=[pr_apply], outputs=[meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])

    btn_apply_0.click(lambda: quick_apply_idx(0), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_apply_1.click(lambda: quick_apply_idx(1), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_apply_2.click(lambda: quick_apply_idx(2), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_apply_3.click(lambda: quick_apply_idx(3), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_apply_4.click(lambda: quick_apply_idx(4), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_apply_5.click(lambda: quick_apply_idx(5), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_apply_6.click(lambda: quick_apply_idx(6), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])
    btn_apply_7.click(lambda: quick_apply_idx(7), outputs=[gr.Code.update(), meta_box, clocks_box, players_box, factions_box, state_json, cfg_auto, cfg_auto_xp, presets_dd, banner_box])


if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="127.0.0.1", server_port=7860)
