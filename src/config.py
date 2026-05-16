"""Configurație globală — încărcare .env, constante BTP Grand Est."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "credentials" / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0") or 0)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PAPPERS_API_KEY = os.getenv("PAPPERS_API_KEY", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SA_FILE = ROOT / os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/google_service_account.json")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")
CLAUDE_MODEL_FAST = os.getenv("CLAUDE_MODEL_FAST", "claude-haiku-4-5-20251001")

GRAND_EST = {"08", "10", "51", "52", "54", "55", "57", "67", "68", "88"}
DEPT_EXCLUS_TOURNEE = {"52", "55", "10", "08"}
NAF_BTP_PREFIXES = ("41", "42", "43")
CPV_BTP_PREFIXES = ("45", "39")

EFFECTIF_MIN = 5
VECHIME_MIN_ANI = 2
CA_MIN = 1_000_000

POINT_DEPART = "43 rue d'Ostwald, Lingolsheim, 67380"
RAYON_TOURNEE_KM = 30
MIN_PROSPECTS_TOURNEE = 5
MAX_PROSPECTS_TOURNEE = 8

CACHE_DIR = ROOT / ".queue"
CACHE_DIR.mkdir(exist_ok=True)


def is_grand_est(dept: str) -> bool:
    return (dept or "").zfill(2) in GRAND_EST


def is_btp_naf(naf: str) -> bool:
    return (naf or "")[:2] in NAF_BTP_PREFIXES
