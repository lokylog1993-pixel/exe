
import typer, json, requests, os

app = typer.Typer(help="CLI для BitD GM AI")

API = os.getenv("GM_API", "http://127.0.0.1:8000/chat")

@app.command()
def chat():
    history: list[dict[str,str]] = []
    typer.echo("Начали. Пишите сообщения. /exit для выхода.")
    while True:
        user = input("> ")
        if user.strip() == "/exit":
            break
        payload = {"history": history, "user": user}
        r = requests.post(API, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        history.append({"role": "user", "content": user})
        history.append({"role": "assistant", "content": data["narration"]})
        typer.echo("\n--- НАРРАТИВ ---\n" + data["narration"])
        if data.get("intent"):
            typer.echo("\n--- INTENT ---\n" + json.dumps(data["intent"], ensure_ascii=False, indent=2))
        if data.get("tool_result"):
            typer.echo("\n--- TOOL RESULT ---\n" + json.dumps(data["tool_result"], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    app()
