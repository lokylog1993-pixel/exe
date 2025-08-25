
from typing import Any, Dict
import os
from dotenv import load_dotenv

def load_env():
    load_dotenv(override=False)

def getenv_str(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name, default)
    return val

def getenv_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))
