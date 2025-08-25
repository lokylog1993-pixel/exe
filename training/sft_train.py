
import textwrap
HELP = textwrap.dedent("""
# OpenAI (пример)
openai datasets create --data data/datasets/openai.jsonl
openai finetunes create --training-file <ID> --model gpt-4o-mini --suffix "bitd-gm"

# Axolotl/LoRA (пример, устанавливается отдельно)
axolotl train path/to/config.yaml  # где указываете data/datasets/chatml.jsonl

# Llama.cpp + LoRA:
# Применение LoRA при инференсе зависит от сборки; см. документацию llama.cpp (--lora).
""")
if __name__ == "__main__":
    print(HELP)
