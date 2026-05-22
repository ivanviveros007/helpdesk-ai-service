import re
import unicodedata
import logging
import pandas as pd

logger = logging.getLogger(__name__)

_MAX_LENGTH = 4000
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EXCESS_WHITESPACE = re.compile(r"[ \t]{2,}")
_EXCESS_NEWLINES = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """
    Limpia y normaliza un texto libre para procesamiento por el LLM.

    Pasos:
    1. Normaliza unicode a NFC
    2. Elimina caracteres de control no imprimibles
    3. Colapsa espacios/tabs múltiples en uno
    4. Colapsa líneas en blanco múltiples (máx 2)
    5. Strip de espacios al inicio/fin
    6. Trunca a MAX_LENGTH caracteres
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    # 1. Normalize unicode
    text = unicodedata.normalize("NFC", text)

    # 2. Remove control chars
    text = _CONTROL_CHARS.sub("", text)

    # 3. Collapse whitespace
    text = _EXCESS_WHITESPACE.sub(" ", text)

    # 4. Collapse blank lines
    text = _EXCESS_NEWLINES.sub("\n\n", text)

    # 5. Strip
    text = text.strip()

    # 6. Truncate
    if len(text) > _MAX_LENGTH:
        logger.debug("Text truncated from %d to %d chars", len(text), _MAX_LENGTH)
        text = text[:_MAX_LENGTH]

    return text


def clean_ticket(asunto: str, descripcion: str) -> dict[str, str]:
    """
    Limpia asunto y descripción de un ticket usando Pandas para
    facilitar futura vectorización batch.
    """
    df = pd.DataFrame([{"asunto": asunto, "descripcion": descripcion}])

    df["asunto"] = df["asunto"].fillna("").apply(clean_text)
    df["descripcion"] = df["descripcion"].fillna("").apply(clean_text)

    row = df.iloc[0]
    return {"asunto": row["asunto"], "descripcion": row["descripcion"]}
