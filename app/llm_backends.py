
from __future__ import annotations
from typing import List
import os

from pydantic import BaseModel
from .utils import getenv_str, getenv_int, load_env

LLAMA_OK = True
OPENAI_OK = True
try:
    from llama_cpp import Llama
except Exception:
    LLAMA_OK = False

try:
    from openai import OpenAI
except Exception:
    OPENAI_OK = False

class ChatTurn(BaseModel):
    role: str
    content: str

class LLM:
    def __init__(self):
        load_env()
        self.backend = getenv_str("LLM_BACKEND", "llama_cpp")
        if self.backend == "llama_cpp" and not LLAMA_OK:
            raise RuntimeError("llama-cpp-python не установлен")
        if self.backend == "openai" and not OPENAI_OK:
            raise RuntimeError("openai не установлен")

        self._model = None
        if self.backend == "llama_cpp":
            path = getenv_str("LLAMA_MODEL_PATH")
            if not path or not os.path.exists(path):
                raise RuntimeError("Укажите LLAMA_MODEL_PATH в .env")
            ctx = getenv_int("LLAMA_CTX_SIZE", 4096)
            self._model = Llama(model_path=path, n_ctx=ctx, logits_all=False, verbose=False)
        else:
            base = getenv_str("OPENAI_BASE_URL", "https://api.openai.com/v1")
            key = getenv_str("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("Требуется OPENAI_API_KEY для openai backend")
            self.client = OpenAI(api_key=key, base_url=base)
            self.model = getenv_str("OPENAI_MODEL", "gpt-4o-mini")

    def chat(self, system_prompt: str, turns: List[ChatTurn], max_tokens: int = 800) -> str:
        if self.backend == "llama_cpp":
            messages = [{"role": "system", "content": system_prompt}] + [t.model_dump() for t in turns]
            out = self._model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.95,
            )
            return out["choices"][0]["message"]["content"]
        else:
            messages = [{"role": "system", "content": system_prompt}] + [t.model_dump() for t in turns]
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                top_p=0.95,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content
