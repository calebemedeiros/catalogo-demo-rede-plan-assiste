import hashlib
import json
import re
import tomllib
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "dist" / "api" / "v2"
CONFIG = tomllib.loads((ROOT / "sources" / "catalog-sources.toml").read_text("utf-8"))
SCHEMA_VERSION = "4.1.0"
FORBIDDEN = {
    "associadoid", "matricula", "matriculas", "pessoafj", "sexo", "observacao",
    "imagem1", "imagem2", "imagem3", "imagem4", "imagem5", "cpf", "carteirinha",
}
ALLOWED_STATUSES = {"updated", "unavailable", "invalid_response"}


def load(path: Path):
    return json.loads(path.read_text("utf-8"))


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


configured_sources = CONFIG.get("sources", [])
allowed_hosts = {urlparse(item["api_url"]).hostname for item in configured_sources}
allowed_hosts |= {
    urlparse(item.get(key)).hostname
    for item in configured_sources
    for key in ("documentation_url", "guide_url")
    if item.get(key)
}


def walk(value, label="root"):
    if isinstance(value, list):
        for index, item in enumerate(value):
            walk(item, f"{label}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            check(key.lower() not in FORBIDDEN, f"Campo proibido: {label}.{key}")
            if key.endswith("url") and item:
                parsed = urlparse(str(item))
                check(
                    (not parsed.scheme and not parsed.hostname and str(item).startswith("./"))
                    or (parsed.scheme == "https" and parsed.hostname in allowed_hosts),
                    f"URL não autorizada: {item}",
                )
            walk(item, f"{label}.{key}")


manifest = load(API / "manifest.json")
check(manifest["schema_version"] == SCHEMA_VERSION, "Contrato diferente de 4.1.0")
check(manifest["environment"] == "production", "Ambiente não produtivo")
check(manifest["publication_status"] in {"approved", "configuration_required"}, "Situação de publicação inválida")
policy = manifest["data_policy"]
check(policy == {
    "acquisition": "documented_public_json_only",
    "raw_responses_published": False,
    "enumeration_allowed": False,
    "automatic_commits": False,
}, "Política de aquisição divergente")

resources = {}
for name, resource in manifest["resources"].items():
    path = API / resource["url"].removeprefix("./")
    check(path.exists(), f"Recurso ausente: {name}")
    check(digest(path) == resource["checksum_sha256"], f"Checksum divergente: {name}")
    resources[name] = load(path)
    check(resources[name]["schema_version"] == SCHEMA_VERSION, f"Versão divergente: {name}")
    walk(resources[name], name)

sources = resources["sources"]["records"]
check(all(item["status"] in ALLOWED_STATUSES for item in sources), "Situação de fonte inválida")
check(len(sources) == len(configured_sources), "Quantidade de fontes divergente")
check(len({item["source_id"] for item in sources}) == len(sources), "Fontes duplicadas")

networks = resources["networks"]["records"]
check(len({item["network_id"] for item in networks}) == len(networks), "Redes duplicadas")
check(all(item["catalog_status"] in {"integrated", "unavailable"} for item in networks), "Situação de rede inválida")

provider_index = resources["providers"]
providers = []
for shard in provider_index["shards"]:
    path = API / "prestadores" / shard["url"].removeprefix("./")
    check(path.exists(), "Fragmento de prestadores ausente")
    check(digest(path) == shard["checksum_sha256"], "Checksum divergente no fragmento")
    payload = load(path)
    walk(payload, "provider_shard")
    providers.extend(payload["records"])
check(len(providers) == provider_index["record_count"], "Contagem de prestadores divergente")
check(len({item["public_id"] for item in providers}) == len(providers), "Prestadores duplicados")

if not configured_sources:
    check(manifest["publication_status"] == "configuration_required", "Catálogo vazio deve exigir configuração")
    check(not providers, "Catálogo inicial não pode conter prestadores")
    check(not resources["networks"]["records"], "Catálogo inicial não pode conter redes")
    check(not resources["specialties"]["records"], "Catálogo inicial não pode conter especialidades")
    check(not resources["procedures"]["records"], "Catálogo inicial não pode conter procedimentos")
else:
    check(manifest["authorization"]["status"] == "authorized", "Fontes configuradas exigem autorização")

build_source = (ROOT / "scripts" / "build_production.py").read_text("utf-8")
check("/api/Buscar" not in build_source, "Endpoint específico não pode ser varrido")
check("search_terms" not in build_source, "Varredura de termos detectada")
check(not re.search(r"[\"'](?:a|e|i|o|u)[\"']\s*,\s*[\"']", build_source), "Possível enumeração detectada")
check(not any("raw" in path.name.lower() for path in API.rglob("*") if path.is_file()), "Resposta bruta presente")

print(
    f"Contrato {SCHEMA_VERSION} válido: {len(configured_sources)} fontes configuradas, "
    f"{len(providers)} prestadores publicados."
)
