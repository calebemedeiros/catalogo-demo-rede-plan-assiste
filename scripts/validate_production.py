import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api" / "v2"
FORBIDDEN = {"associadoId","matricula","pessoaFJ","sexo","observacao","imagem1","imagem2","imagem3","imagem4","imagem5","cpf","carteirinha"}
ALLOWED_HOSTS = {"planassiste.mpu.mp.br","www.encontreseumedico.com.br","coopmedrs.com.br","www.unimed.coop.br","www.unimednacional.coop.br","www.unimedrecife.com.br","www.unimedriopreto.com.br","api-esm.amhp.com.br","consulta-ocl.apps.sa-1a.mendixcloud.com","www.gov.br"}

def load(path):
    return json.loads(path.read_text("utf-8"))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(condition, message):
    if not condition:
        raise AssertionError(message)

def walk(value, label="root"):
    if isinstance(value, list):
        for index, item in enumerate(value): walk(item, f"{label}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            check(key.lower() not in {x.lower() for x in FORBIDDEN}, f"Campo proibido: {label}.{key}")
            if key.endswith("url") and item:
                parsed = urlparse(item)
                check((not parsed.scheme and not parsed.hostname and str(item).startswith("./")) or (parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS), f"URL não autorizada: {item}")
            walk(item, f"{label}.{key}")

manifest = load(API / "manifest.json")
check(manifest["schema_version"] == "4.0.0", "Contrato diferente de 4.0.0")
check(manifest["environment"] == "production", "Ambiente não produtivo")
check(manifest["publication_status"] == "approved", "Publicação não aprovada")
check(manifest["authorization"]["status"] == "authorized", "Autorização ausente")
walk(manifest)

resources = {}
for name, resource in manifest["resources"].items():
    path = API / resource["url"].removeprefix("./")
    check(path.exists(), f"Recurso ausente: {name}")
    check(digest(path) == resource["checksum_sha256"], f"Checksum divergente: {name}")
    resources[name] = load(path)
    walk(resources[name], name)

network_ids = {item["network_id"] for item in resources["networks"]["records"]}
specialty_ids = {item["specialty_id"] for item in resources["specialties"]["records"]}
check(len(network_ids) == resources["networks"]["record_count"], "Redes duplicadas")
check(len(specialty_ids) == resources["specialties"]["record_count"], "Especialidades duplicadas")

index = resources["providers"]
providers = []
for shard in index["shards"]:
    path = API / "prestadores" / shard["url"].removeprefix("./")
    check(digest(path) == shard["checksum_sha256"], f"Checksum divergente no shard {shard['source_id']}")
    payload = load(path)
    check(payload["record_count"] == len(payload["records"]), "Contagem divergente no shard")
    providers.extend(payload["records"])
check(len(providers) == index["record_count"] and providers, "Catálogo de prestadores vazio ou inconsistente")

provider_ids = set()
for item in providers:
    check(item["public_id"] not in provider_ids, f"Prestador duplicado: {item['public_id']}")
    provider_ids.add(item["public_id"])
    check(item["source_id"] in {source["source_id"] for source in resources["sources"]["records"]}, "Fonte inexistente")
    check(all(link["network_id"] in network_ids for link in item["network_links"]), "Vínculo com rede inexistente")
    check(all(sid in specialty_ids for sid in item["specialty_ids"]), "Especialidade inexistente")
    check(item["type"] in {"professional","facility"}, "Tipo de prestador inválido")

procedures = resources["procedures"]["records"]
check(procedures, "Catálogo TUSS vazio")
procedure_ids = set()
mapped = 0
for item in procedures:
    check(item["procedure_id"] not in procedure_ids and re.fullmatch(r"tuss-\d{8,10}", item["procedure_id"]), "Procedimento inválido ou duplicado")
    procedure_ids.add(item["procedure_id"])
    check(all(sid in specialty_ids for sid in item["related_specialty_ids"]), "Procedimento relacionado a especialidade inexistente")
    if item["related_specialty_ids"]:
        check(item["mapping_type"] == "official_crosswalk" and item["sigtap_codes"] and item["cbo_codes"], "Associação sem cadeia oficial completa")
        mapped += 1
check(mapped > 0, "Nenhum procedimento possui relação oficial completa")
print(f"Contrato 4.0.0 válido: {len(providers)} prestadores, {len(procedures)} procedimentos, {mapped} com especialidades relacionadas.")
