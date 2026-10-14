from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tomllib
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "sources" / "catalog-sources.toml"
OUTPUT = ROOT / "dist" / "api" / "v2"
SCHEMA_VERSION = "4.1.0"
ALLOWED_RELATIONSHIPS = {"direct_agreement", "indirect_agreement"}


def normalize(value: str | None) -> str:
    decomposed = unicodedata.normalize("NFD", str(value or ""))
    ascii_value = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def clean_text(value):
    if value is None:
        return None
    result = re.sub(r"\s+", " ", str(value)).strip()
    return result or None


def nested_value(value, path: str | None):
    if not path:
        return None
    current = value
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write_json(root: Path, relative_path: str, value) -> str:
    payload = json_bytes(value)
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def public_json(session: requests.Session, url: str):
    response = session.get(
        url,
        timeout=(15, 90),
        headers={"Accept": "application/json", "User-Agent": "Plan-Assiste-Catalog/1.1"},
        allow_redirects=False,
    )
    response.raise_for_status()
    if "json" not in response.headers.get("content-type", "").lower():
        raise RuntimeError("A fonte não respondeu em JSON.")
    return response.json(), response.status_code


def extract_records(payload, path: str):
    records = payload if not path else nested_value(payload, path)
    if not isinstance(records, list):
        raise RuntimeError("O caminho configurado não aponta para uma lista JSON.")
    return records


def normalize_record(raw, source, specialty_index):
    fields = source.get("fields", {})
    public_id = clean_text(nested_value(raw, fields.get("public_id")))
    display_name = clean_text(nested_value(raw, fields.get("display_name")))
    if not public_id or not display_name:
        return None

    specialty_name = clean_text(nested_value(raw, fields.get("specialty_name")))
    specialty_ids = []
    specialties = []
    if specialty_name:
        specialty_id = normalize(specialty_name)
        if specialty_id:
            specialty_ids.append(specialty_id)
            specialties.append({"specialty_id": specialty_id, "name": specialty_name, "rqe": None})
            specialty_index.setdefault(specialty_id, {
                "specialty_id": specialty_id,
                "name": specialty_name,
                "source_id": source["source_id"],
            })

    provider_type = clean_text(nested_value(raw, fields.get("provider_type")))
    provider_type = "facility" if normalize(provider_type) in {"facility", "estabelecimento", "clinica", "hospital"} else "professional"

    council_number = clean_text(nested_value(raw, fields.get("council_number")))
    registry = None
    if council_number:
        registry = {
            "council": clean_text(nested_value(raw, fields.get("council"))),
            "state": clean_text(nested_value(raw, fields.get("council_state"))),
            "number": council_number,
        }

    address = {
        "street": clean_text(nested_value(raw, fields.get("street"))),
        "district": clean_text(nested_value(raw, fields.get("district"))),
        "city": clean_text(nested_value(raw, fields.get("city"))),
        "state": clean_text(nested_value(raw, fields.get("state"))),
    }
    phone = clean_text(nested_value(raw, fields.get("phone")))
    location = {
        "facility_name": clean_text(nested_value(raw, fields.get("facility_name"))),
        "address": address,
        "phones": [phone] if phone else [],
        "modality": "in_person",
    }

    return {
        "public_id": f"{source['source_id']}-{normalize(public_id)}",
        "type": provider_type,
        "display_name": display_name,
        "professional_registry": registry,
        "specialty_ids": specialty_ids,
        "specialties": specialties,
        "service_locations": [location],
        "network_links": [{
            "network_id": source["network_id"],
            "relationship": source["relationship"],
            "verification": "public_json_api",
            "guide_url": source.get("guide_url"),
        }],
        "source_id": source["source_id"],
    }


def validate_source_config(source):
    required = {"source_id", "network_id", "network_name", "relationship", "api_url", "records_path", "fields"}
    missing = sorted(required - source.keys())
    if missing:
        raise RuntimeError(f"Fonte incompleta: {', '.join(missing)}")
    if source["relationship"] not in ALLOWED_RELATIONSHIPS:
        raise RuntimeError("relationship deve ser direct_agreement ou indirect_agreement.")
    if not str(source["api_url"]).startswith("https://"):
        raise RuntimeError("A API deve usar HTTPS.")
    for field in ("public_id", "display_name"):
        if not source["fields"].get(field):
            raise RuntimeError(f"Mapeamento obrigatório ausente: {field}")


def main():
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    config = tomllib.loads(CONFIG_PATH.read_text("utf-8"))
    configured_sources = config.get("sources", [])
    authorization = config.get("authorization", {"status": "configuration_required", "reference": ""})
    session = requests.Session()
    providers = []
    networks = []
    source_reports = []
    specialty_index = {}

    for source in configured_sources:
        validate_source_config(source)
        networks.append({
            "network_id": source["network_id"],
            "name": source["network_name"],
            "relationship": source["relationship"],
            "classification": "configured_public_api",
            "territory": source.get("territory"),
            "guide_url": source.get("guide_url"),
            "source_id": source["source_id"],
            "catalog_status": "integrated",
        })
        try:
            payload, http_status = public_json(session, source["api_url"])
            raw_records = extract_records(payload, source["records_path"])
            normalized = [normalize_record(item, source, specialty_index) for item in raw_records]
            normalized = [item for item in normalized if item]
            providers.extend(normalized)
            networks[-1]["catalog_status"] = "integrated"
            source_reports.append({
                "source_id": source["source_id"],
                "name": source["network_name"],
                "organization": source.get("organization"),
                "url": source["api_url"],
                "documentation_url": source.get("documentation_url"),
                "integration_type": "public_json_api",
                "relationship": source["relationship"],
                "last_attempt_at": generated_at,
                "record_count_received": len(raw_records),
                "record_count_published": len(normalized),
                "status": "updated",
                "http_status": http_status,
            })
        except Exception as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            networks[-1]["catalog_status"] = "unavailable"
            source_reports.append({
                "source_id": source["source_id"],
                "name": source["network_name"],
                "organization": source.get("organization"),
                "url": source["api_url"],
                "documentation_url": source.get("documentation_url"),
                "integration_type": "public_json_api",
                "relationship": source["relationship"],
                "last_attempt_at": generated_at,
                "record_count_received": 0,
                "record_count_published": 0,
                "status": "unavailable",
                "http_status": status,
                "status_note": "Nenhuma rota alternativa foi utilizada.",
            })

    providers.sort(key=lambda item: normalize(item["display_name"]))
    specialties = sorted(specialty_index.values(), key=lambda item: normalize(item["name"]))
    envelope = lambda records: {
        "schema_version": SCHEMA_VERSION,
        "environment": "production",
        "generated_at": generated_at,
        "record_count": len(records),
        "records": records,
    }

    dist_root = ROOT / "dist"
    if dist_root.exists():
        shutil.rmtree(dist_root)
    candidate = dist_root / ".candidate-api-v2"
    try:
        shards = []
        if providers:
            shard_hash = write_json(candidate, "prestadores/configured-sources.json", envelope(providers))
            shards.append({
                "source_id": "configured-sources",
                "url": "./configured-sources.json",
                "record_count": len(providers),
                "checksum_sha256": shard_hash,
            })
        provider_index = {
            "schema_version": SCHEMA_VERSION,
            "environment": "production",
            "generated_at": generated_at,
            "record_count": len(providers),
            "shards": shards,
        }
        resources = {
            "providers": ("prestadores/index.json", provider_index),
            "networks": ("redes.json", envelope(networks)),
            "specialties": ("especialidades.json", envelope(specialties)),
            "procedures": ("procedimentos.json", envelope([])),
            "sources": ("fontes.json", envelope(source_reports)),
        }
        hashes = {name: write_json(candidate, path, value) for name, (path, value) in resources.items()}
        write_json(candidate, "indices/busca-geral.json", envelope([]))
        write_json(candidate, "indices/procedimentos.json", envelope([]))
        write_json(candidate, "indices/localidades.json", envelope([]))
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "environment": "production",
            "generated_at": generated_at,
            "publication_status": "approved" if configured_sources and authorization.get("status") == "authorized" else "configuration_required",
            "authorization": {
                "status": authorization.get("status", "configuration_required"),
                "reference": clean_text(authorization.get("reference")),
            },
            "data_policy": {
                "acquisition": "documented_public_json_only",
                "raw_responses_published": False,
                "enumeration_allowed": False,
                "automatic_commits": False,
            },
            "resources": {
                name: {"url": f"./{path}", "checksum_sha256": hashes[name]}
                for name, (path, _) in resources.items()
            },
            "sources": [item["source_id"] for item in source_reports],
            "metrics": {
                "providers": len(providers),
                "procedures": 0,
                "networks": len(networks),
                "specialties": len(specialties),
                "integrated_provider_sources": sum(item["status"] == "updated" for item in source_reports),
            },
        }
        write_json(candidate, "manifest.json", manifest)
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(candidate, OUTPUT)
    finally:
        if candidate.exists():
            shutil.rmtree(candidate)

    print(json.dumps(manifest["metrics"], ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
