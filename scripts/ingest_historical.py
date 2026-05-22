"""
Script de ingesta inicial de tickets históricos a ChromaDB.

Uso:
    python scripts/ingest_historical.py --file data/tickets_historicos.json

El JSON de entrada debe tener la siguiente estructura:
[
  {
    "ticket_id": "hist-001",
    "asunto": "App crashea en iOS",
    "descripcion": "Descripción del problema...",
    "category": "mobile_crash",
    "priority": 8,
    "suggested_level": 2,
    "resolution_summary": "Se identificó un bug en PaymentViewModel..."
  },
  ...
]
"""

import sys
import json
import argparse
import logging

# Add project root to path
sys.path.insert(0, ".")

from app.core.logging import setup_logging
from app.pipeline.cleaner import clean_text
from app.pipeline.embedder import embed_text
from app.rag.vector_store import add_ticket_to_store, get_collection

setup_logging()
logger = logging.getLogger("ingest_historical")


def ingest(file_path: str, dry_run: bool = False) -> None:
    with open(file_path, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    logger.info("Loaded %d historical tickets from %s", len(tickets), file_path)

    collection = get_collection()
    existing_ids = set(collection.get()["ids"])
    logger.info("Collection already has %d documents", len(existing_ids))

    ingested = 0
    skipped = 0

    for ticket in tickets:
        tid = ticket["ticket_id"]

        if tid in existing_ids:
            logger.debug("Skipping already-ingested ticket %s", tid)
            skipped += 1
            continue

        full_text = clean_text(f"{ticket['asunto']}\n\n{ticket['descripcion']}")
        metadata = {
            "asunto": ticket["asunto"],
            "category": ticket.get("category", ""),
            "priority": ticket.get("priority", 0),
            "suggested_level": ticket.get("suggested_level", 1),
            "resolution_summary": ticket.get("resolution_summary", "Sin resolución documentada."),
        }

        if dry_run:
            logger.info("[DRY RUN] Would ingest ticket %s: %s", tid, ticket["asunto"])
            ingested += 1
            continue

        embedding = embed_text(full_text)
        add_ticket_to_store(tid, full_text, metadata, embedding)
        ingested += 1
        logger.info("Ingested ticket %s (%d/%d)", tid, ingested, len(tickets) - skipped)

    logger.info(
        "Done. Ingested: %d | Skipped (already existed): %d",
        ingested,
        skipped,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest historical tickets into ChromaDB")
    parser.add_argument("--file", required=True, help="Path to JSON file with historical tickets")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    args = parser.parse_args()

    ingest(args.file, dry_run=args.dry_run)
