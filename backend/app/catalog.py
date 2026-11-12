import json
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.json"

@lru_cache(maxsize=1)
def load_catalog() -> dict:
    with CATALOG_PATH.open(encoding="utf-8") as file:
        return json.load(file)

def ability(ability_id: str) -> dict | None:
    return next((entry for entry in load_catalog()["abilities"] if entry["id"] == ability_id), None)
