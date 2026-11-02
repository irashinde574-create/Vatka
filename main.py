"""Vakta — voice-first ledger for local Indian businesses, powered by Sarvam AI."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"
DB_PATH = BASE_DIR / "vakta.db"
SARVAM_TIMEOUT_SECONDS = 25.0

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "customer_name": {"type": "string"},
        "service_item": {"type": "string"},
        "time_slot": {"type": "string"},
        "payment_status": {"type": "string"},
        "amount": {"type": "string"},
        "confirmation_message": {"type": "string"},
    },
    "required": [
        "customer_name",
        "service_item",
        "time_slot",
        "payment_status",
        "amount",
        "confirmation_message",
    ],
    "additionalProperties": False,
}

EXTRACT_SYSTEM = (
    "You extract business order details from Indian vendor voice notes. "
    "The input may be Hindi, Marathi, English, or code-mixed Hinglish. "
    "Return JSON only. Use empty string when a field is missing. "
    "payment_status must be one of: paid, unpaid, partial, unknown. "
    "confirmation_message must be a short spoken confirmation in Hindi (Devanagari script), "
    "mentioning customer, item, time, and amount when known."
)


class AudioGenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2500)
    language_code: str = Field(default="hi-IN")


class LedgerEntryIn(BaseModel):
    customer_name: str = ""
    service_item: str = ""
    time_slot: str = ""
    payment_status: str = "unknown"
    amount: str = ""
    transcript: str = ""
    confirmation_message: str = ""


app = FastAPI(title="Vakta")


def get_api_key() -> str:
    return (os.getenv("SARVAM_API_KEY") or "").strip()


def get_client() -> SarvamAI:
    key = get_api_key()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="SARVAM_API_KEY is missing. Paste your key into the .env file and restart.",
        )
    return SarvamAI(api_subscription_key=key, timeout=SARVAM_TIMEOUT_SECONDS)


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                customer_name TEXT,
                service_item TEXT,
                time_slot TEXT,
                payment_status TEXT,
                amount TEXT,
                transcript TEXT,
                confirmation_message TEXT
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def home() -> FileResponse:
    if not TEMPLATE_PATH.exists():
        raise HTTPException(status_code=500, detail="Frontend template is missing.")
    return FileResponse(TEMPLATE_PATH)


def _parse_json_content(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def mock_extract(transcript: str) -> dict[str, Any]:
    """Offline/demo parser so the stage demo still works if Sarvam times out."""
    text = transcript.strip() or "Ramesh ka tiffin order, shaam 7 baje, 150 rupaye unpaid"
    lowered = text.lower()
    amount_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:rs|inr|rupee|rupaye|₹)?", lowered)
    time_match = re.search(
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|baje)?)|(shaam|subah|dopahar|raat|morning|evening|night)",
        lowered,
    )
    paid = "paid"
    if any(w in lowered for w in ("unpaid", "udhaar", "baad mein", "pending", "nahi diya")):
        paid = "unpaid"
    elif "partial" in lowered or "aadha" in lowered:
        paid = "partial"

    words = [w for w in re.split(r"[\s,]+", text) if w]
    customer = words[0].strip(".,") if words else "Customer"
    return {
        "customer_name": customer[:40],
        "service_item": text[:80],
        "time_slot": time_match.group(0) if time_match else "",
        "payment_status": paid,
        "amount": amount_match.group(1) if amount_match else "",
        "confirmation_message": "आपका ऑर्डर कन्फर्म हो गया है। धन्यवाद!",
        "transcript": text,
        "used_mock": True,
    }


def extract_intent(client: SarvamAI, transcript: str) -> dict[str, Any]:
    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": transcript},
        ],
        temperature=0.2,
        reasoning_effort="none",
        max_tokens=512,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "voice_order",
                "strict": True,
                "schema": INTENT_SCHEMA,
            },
        },
        request_options={"timeout_in_seconds": SARVAM_TIMEOUT_SECONDS, "max_retries": 1},
    )
    content = response.choices[0].message.content or "{}"
    data = _parse_json_content(content)
    data["transcript"] = transcript
    data["used_mock"] = False
    return data


def transcribe_audio(client: SarvamAI, filename: str, content: bytes, content_type: str) -> tuple[str, Optional[str]]:
    file_tuple = (filename or "recording.webm", BytesIO(content), content_type or "audio/webm")
    result = client.speech_to_text.transcribe(
        file=file_tuple,
        model="saaras:v4",
        mode="codemix",
        keyterms=["tiffin", "order", "udhaar", "WhatsApp", "mechanic", "kirana"],
        request_options={"timeout_in_seconds": SARVAM_TIMEOUT_SECONDS, "max_retries": 1},
    )
    return result.transcript, result.language_code


def describe_sarvam_error(exc: Exception) -> str:
    if isinstance(exc, ApiError):
        if exc.status_code == 403:
            return "Sarvam rejected the API key. Check SARVAM_API_KEY in .env."
        if exc.status_code == 402:
            return "Sarvam credits are exhausted."
        if exc.status_code == 429:
            return "Sarvam rate limit hit. Wait a moment and try again."
        return f"Sarvam API error ({exc.status_code})."
    name = type(exc).__name__.lower()
    if "timeout" in name or "timeout" in str(exc).lower():
        return "Sarvam timed out."
    return str(exc) or "Sarvam request failed."


@app.post("/api/process-voice")
def process_voice(audio: UploadFile = File(...)) -> dict[str, Any]:
    content = audio.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio buffer. Hold the mic and speak, then release.")

    filename = audio.filename or "recording.webm"
    content_type = audio.content_type or "audio/webm"
    warnings: list[str] = []
    transcript = ""
    language_code: Optional[str] = None
    parsed: dict[str, Any]

    try:
        client = get_client()
        try:
            transcript, language_code = transcribe_audio(client, filename, content, content_type)
        except Exception as exc:
            warnings.append(describe_sarvam_error(exc) + " Using mock transcript.")
            transcript = "Ramesh ka tiffin order shaam saat baje, 150 rupaye unpaid"
            parsed = mock_extract(transcript)
            parsed["language_code"] = "hi-IN"
            parsed["warnings"] = warnings
            return parsed

        if not transcript.strip():
            warnings.append("Transcription was empty. Using mock parser.")
            parsed = mock_extract("empty recording")
        else:
            try:
                parsed = extract_intent(client, transcript)
            except Exception as exc:
                warnings.append(describe_sarvam_error(exc) + " Using mock parser.")
                parsed = mock_extract(transcript)
    except HTTPException:
        raise
    except Exception as exc:
        warnings.append(describe_sarvam_error(exc) + " Using mock parser.")
        parsed = mock_extract("Ramesh ka tiffin order shaam saat baje, 150 rupaye unpaid")

    parsed["language_code"] = language_code or "hi-IN"
    parsed["warnings"] = warnings
    parsed["transcript"] = transcript or parsed.get("transcript", "")
    return parsed


@app.post("/api/generate-audio")
def generate_audio(body: AudioGenerateRequest) -> dict[str, Any]:
    language = body.language_code if body.language_code else "hi-IN"
    if language not in {
        "bn-IN",
        "en-IN",
        "gu-IN",
        "hi-IN",
        "kn-IN",
        "ml-IN",
        "mr-IN",
        "od-IN",
        "pa-IN",
        "ta-IN",
        "te-IN",
    }:
        language = "hi-IN"

    try:
        client = get_client()
        response = client.text_to_speech.convert(
            text=body.text[:2500],
            language_code=language,
            model="bulbul:v4-flash",
            speaker="shubh_enhi_ads",
            request_options={"timeout_in_seconds": SARVAM_TIMEOUT_SECONDS, "max_retries": 1},
        )
        audios = list(response.audios or [])
        if not audios:
            raise HTTPException(status_code=502, detail="Bulbul returned no audio.")
        return {"audio_base64": "".join(audios), "mime_type": "audio/wav", "used_mock": False}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=describe_sarvam_error(exc)) from exc


@app.get("/api/ledger")
def list_ledger() -> dict[str, Any]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM ledger ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    return {"entries": [dict(row) for row in rows]}


@app.post("/api/ledger")
def add_ledger(entry: LedgerEntryIn) -> dict[str, Any]:
    record = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "customer_name": entry.customer_name,
        "service_item": entry.service_item,
        "time_slot": entry.time_slot,
        "payment_status": entry.payment_status,
        "amount": entry.amount,
        "transcript": entry.transcript,
        "confirmation_message": entry.confirmation_message,
    }
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO ledger (
                id, created_at, customer_name, service_item, time_slot,
                payment_status, amount, transcript, confirmation_message
            ) VALUES (
                :id, :created_at, :customer_name, :service_item, :time_slot,
                :payment_status, :amount, :transcript, :confirmation_message
            )
            """,
            record,
        )
        conn.commit()
    return record
