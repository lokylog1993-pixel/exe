
"""
Готовит датасет для SFT из `data/logs/chat.jsonl`.
Выход:
- data/datasets/openai.jsonl
- data/datasets/chatml.jsonl
"""
import json, os, argparse

def load_logs(path="data/logs/chat.jsonl"):
    if not os.path.exists(path):
        raise SystemExit(f"Не найден лог {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def make_openai_messages(rec, system_prompt: str):
    messages = [{"role": "system", "content": system_prompt}]
    for h in rec.get("history", []):
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role":"user", "content": rec["user"]})
    target = rec.get("assistant_raw") or rec.get("assistant_narration","")
    messages.append({"role":"assistant","content": target})
    return messages

def make_chatml(rec, system_prompt: str):
    parts = [f"<|system|>\n{system_prompt}"]
    for h in rec.get("history", []):
        parts.append(f"<|{h['role']}|>\n{h['content']}")
    parts.append(f"<|user|>\n{rec['user']}")
    inp = "\n".join(parts)
    out = rec.get("assistant_raw") or rec.get("assistant_narration","")
    return {"input": inp, "output": out}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system-prompt-path", default="app/prompts.py")
    ap.add_argument("--out-openai", default="data/datasets/openai.jsonl")
    ap.add_argument("--out-chatml", default="data/datasets/chatml.jsonl")
    args = ap.parse_args()

    with open(args.system_prompt_path, "r", encoding="utf-8") as f:
        txt = f.read()
    start = txt.find("SYSTEM_PROMPT_RU =")
    q1 = txt.find('"""', start)
    q2 = txt.find('"""', q1+3)
    system_prompt = txt[q1+3:q2]

    os.makedirs("data/datasets", exist_ok=True)
    with open(args.out_openai, "w", encoding="utf-8") as f1, open(args.out_chatml, "w", encoding="utf-8") as f2:
        for rec in load_logs():
            messages = make_openai_messages(rec, system_prompt)
            f1.write(json.dumps({ "messages": messages }, ensure_ascii=False) + "\n")
            f2.write(json.dumps(make_chatml(rec, system_prompt), ensure_ascii=False) + "\n")
    print("Готово:", args.out_openai, "и", args.out_chatml)

if __name__ == "__main__":
    main()
