from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import requests
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "api" / "v2"
SCHEMA_VERSION = "4.0.0"
AMHP_BASE = os.getenv("AMHP_BASE_URL", "https://api-esm.amhp.com.br").rstrip("/")
AMHP_NETWORK_ID = 639
ANS_CROSSWALK = "https://www.gov.br/ans/pt-br/arquivos/assuntos/prestadores/padrao-para-troca-de-informacao-de-saude-suplementar-tiss/padrao-tiss-tabelas-relacionadas/padraotiss_mapeamento_tuss_sigtap.zip"
SIGTAP_ARCHIVE = os.getenv("SIGTAP_ARCHIVE_URL", "https://raw.githubusercontent.com/RenatoKR/SIGTAP/main/tabelas/TabelaUnificada_202609_v2610050950.zip")
TUSS_SOURCE = "https://consulta-ocl.apps.sa-1a.mendixcloud.com/rest/oclservice/ANS/source"


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFD", str(value or ""))
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in value if unicodedata.category(c) != "Mn").lower()).strip("-")


def text(value) -> str | None:
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value or None


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def stable_id(prefix: str, value) -> str:
    digest = hashlib.sha256(f"{prefix}:{value}".encode()).hexdigest()[:16]
    return f"{prefix}-{digest}"


def get_json(session: requests.Session, url: str, params=None, attempts=4):
    last = None
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, timeout=(15, 120), headers={"Accept": "application/json", "User-Agent": "Plan-Assiste-Catalog/1.0"})
            response.raise_for_status()
            if "json" not in response.headers.get("content-type", "").lower():
                raise RuntimeError(f"Resposta não JSON em {response.url}")
            return response.json()
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Falha ao consultar {url}: {last}")


def download(session: requests.Session, url: str, target: Path):
    with session.get(url, timeout=(20, 240), stream=True, headers={"User-Agent": "Plan-Assiste-Catalog/1.0"}) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    handle.write(chunk)


def collect_amhp(session: requests.Session, verified_date: str):
    specialties_raw = get_json(session, f"{AMHP_BASE}/api/Especialidades")
    specialties = {item["id"]: {"specialty_id": norm(item["nome"]), "name": text(item["nome"]), "external_id": str(item["id"])} for item in specialties_raw}

    # A API não publica paginação para /api/Buscar. A união de buscas amplas mantém
    # o filtro oficial do convênio 639 e evita depender de uma única consulta.
    search_terms = ["a", "e", "i", "o", "u"]

    def fetch(term):
        return term, get_json(session, f"{AMHP_BASE}/api/Buscar", {"q": term, "o": AMHP_NETWORK_ID})

    people = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch, term): term for term in search_terms}
        for future in concurrent.futures.as_completed(futures):
            term = futures[future]
            try:
                _, rows = future.result()
                for row in rows:
                    if row.get("associadoId") is not None:
                        people[str(row["associadoId"])] = row
            except Exception as exc:
                failures.append(f"busca '{term}': {exc}")
    if failures:
        raise RuntimeError("Falha em especialidades AMHPDF: " + " | ".join(failures[:5]))
    if len(people) < 10000:
        raise RuntimeError(f"A fonte AMHPDF retornou volume abaixo do limite de segurança: {len(people)}.")

    records = []
    for internal_id, row in people.items():
        row_specialties = []
        specialty_ids = []
        for item in row.get("especialidades") or []:
            sid = norm(item.get("nome"))
            if not sid:
                continue
            specialty_ids.append(sid)
            row_specialties.append({"specialty_id": sid, "name": text(item.get("nome")), "rqe": text(item.get("rqecrm"))})
            specialties.setdefault(item.get("id"), {"specialty_id": sid, "name": text(item.get("nome")), "external_id": str(item.get("id") or "")})
        locations = []
        for address in row.get("enderecos") or []:
            state = text(address.get("estado"))
            city = text(address.get("cidade"))
            if not state and not city:
                continue
            locations.append({
                "facility_name": text(row.get("nome")) if row.get("pessoaFJ") else None,
                "address": {"street": text(address.get("logradouro")), "district": text(address.get("bairro")), "city": city, "state": state},
                "phones": [phone for phone in [text(row.get("telefone1")), text(row.get("telefone2"))] if phone],
                "modality": "in_person"
            })
        pessoa_fj = row.get("pessoaFJ")
        is_facility = pessoa_fj is True or str(pessoa_fj).upper() in {"J", "PJ", "TRUE", "1"}
        registry = None
        council_number = text(row.get("codigoConselho"))
        if not is_facility and council_number:
            registry = {"council": text(row.get("conselho")) or "CRM", "state": next((loc["address"]["state"] for loc in locations if loc["address"]["state"]), None), "number": council_number}
        records.append({
            "public_id": stable_id("amhp", internal_id),
            "type": "facility" if is_facility else "professional",
            "display_name": text(row.get("nome")) or "Prestador sem nome de divulgação",
            "professional_registry": registry,
            "specialty_ids": sorted(set(specialty_ids)),
            "specialties": row_specialties,
            "service_locations": locations,
            "network_links": [{"network_id": "amhpdf", "relationship": "direct_agreement", "verification": "official_api", "guide_url": "https://www.encontreseumedico.com.br/"}],
            "source_id": "amhp-api",
            "source_updated_at": verified_date,
            "verified_at": verified_date
        })
    records.sort(key=lambda item: norm(item["display_name"]))
    return records, sorted(specialties.values(), key=lambda item: norm(item["name"]))


def read_fixed(path: Path, widths, encoding="latin1"):
    with path.open("r", encoding=encoding, errors="replace") as handle:
        for line in handle:
            position = 0
            row = []
            for width in widths:
                row.append(line[position:position + width].strip())
                position += width
            yield row


def cbo_specialties(cbo_name: str, specialties):
    value = norm(cbo_name)
    aliases = {
        "cardiologista": "cardiologia", "pediatra": "pediatria", "psiquiatra": "psiquiatria",
        "psicologo": "psicologia", "fisioterapeuta": "fisioterapia", "fonoaudiologo": "fonoaudiologia",
        "nutricionista": "nutricao", "terapeuta-ocupacional": "terapia-ocupacional", "urologista": "urologia",
        "dermatologista": "dermatologia", "ginecologista": "ginecologia-e-obstetricia", "oftalmologista": "oftalmologia",
        "neurologista": "neurologia", "neurocirurgiao": "neurocirurgia", "infectologista": "infectologia",
        "hematologista": "hematologia-e-hemoterapia", "oncologista": "oncologia-clinica", "radioterapeuta": "radioterapia",
        "endocrinologista": "endocrinologia-e-metabologia", "gastroenterologista": "gastroenterologia",
        "nefrologista": "nefrologia", "pneumologista": "pneumologia", "reumatologista": "reumatologia",
        "otorrinolaringologista": "otorrinolaringologia", "geriatra": "geriatria", "geneticista": "genetica-medica",
        "clinico": "clinica-medica", "medico-da-familia": "medicina-de-familia-e-comunidade"
    }
    available = {item["specialty_id"] for item in specialties}
    matched = {sid for keyword, sid in aliases.items() if keyword in value and sid in available}
    return matched


def collect_procedures(session: requests.Session, work: Path, specialties):
    cross_zip, sigtap_zip = work / "crosswalk.zip", work / "sigtap.zip"
    download(session, ANS_CROSSWALK, cross_zip)
    download(session, SIGTAP_ARCHIVE, sigtap_zip)
    cross_dir, sigtap_dir = work / "crosswalk", work / "sigtap"
    with zipfile.ZipFile(cross_zip) as archive:
        archive.extractall(cross_dir)
    with zipfile.ZipFile(sigtap_zip) as archive:
        archive.extractall(sigtap_dir)

    tuss_names = {code: name for code, name in read_fixed(sigtap_dir / "tb_tuss.txt", [10, 450]) if code != "00000000"}
    sigtap_names = {row[0]: row[1] for row in read_fixed(sigtap_dir / "tb_procedimento.txt", [10, 250])}
    cbo_names = {row[0]: row[1] for row in read_fixed(sigtap_dir / "tb_ocupacao.txt", [6, 150])}
    procedure_cbos = defaultdict(set)
    for procedure, cbo, _ in read_fixed(sigtap_dir / "rl_procedimento_ocupacao.txt", [10, 6, 6]):
        procedure_cbos[procedure].add(cbo)

    workbook = openpyxl.load_workbook(next(cross_dir.glob("*.xlsx")), read_only=True, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    crosswalk = defaultdict(set)
    for row in sheet.iter_rows(min_row=2, values_only=True):
        tuss, _, sigtap, _, status, *_ = row
        tuss = str(tuss or "").split(".")[0].zfill(8)
        sigtap = str(sigtap or "").split(".")[0].zfill(10)
        if status and "mapeado" in norm(status) and tuss in tuss_names and sigtap in sigtap_names:
            crosswalk[tuss].add(sigtap)
    workbook.close()

    procedures = []
    for code, name in tuss_names.items():
        sigtap_codes = sorted(crosswalk.get(code, set()))
        cbos = sorted({cbo for sigtap in sigtap_codes for cbo in procedure_cbos.get(sigtap, set())})
        related = sorted({sid for cbo in cbos for sid in cbo_specialties(cbo_names.get(cbo, ""), specialties)})
        procedures.append({
            "procedure_id": f"tuss-{code}", "terminology": "TUSS", "code": code, "name": name,
            "sigtap_codes": sigtap_codes, "cbo_codes": cbos, "related_specialty_ids": related,
            "mapping_type": "official_crosswalk" if sigtap_codes else "unmapped",
            "source_competence": {"tuss": "202609", "tuss_sigtap_crosswalk": "201704", "sigtap": "202609"}
        })
    return procedures


def telemedicine_records(config, specialties, verified_date):
    by_name = {norm(item["name"]): item for item in specialties}
    records = []
    for item in config["telemedicine"]:
        normalized = []
        for name in item["specialties"]:
            sid = norm(name)
            normalized.append(sid)
            by_name.setdefault(sid, {"specialty_id": sid, "name": name, "external_id": None})
        records.append({
            "public_id": item["provider_id"], "type": "facility", "display_name": item["name"],
            "professional_registry": None, "specialty_ids": sorted(set(normalized)),
            "specialties": [{"specialty_id": sid, "name": by_name[sid]["name"], "rqe": None} for sid in sorted(set(normalized))],
            "service_locations": [{"facility_name": item["name"], "address": {"street": None, "district": None, "city": None, "state": None}, "phones": [], "modality": "remote"}],
            "network_links": [{"network_id": "telemedicina", "relationship": "direct_agreement", "verification": "official_page", "guide_url": item["access_url"]}],
            "source_id": "plan-assiste-telemedicina", "source_updated_at": verified_date, "verified_at": verified_date,
            "availability": item["availability"], "restriction": item.get("restriction")
        })
    return records, sorted(by_name.values(), key=lambda value: norm(value["name"]))


def load_last_approved_amhp():
    """Retém a última extração aprovada quando a API bloqueia o coletor remoto."""
    provider_path = OUTPUT / "prestadores" / "amhp-df.json"
    specialty_path = OUTPUT / "especialidades.json"
    if not provider_path.exists() or not specialty_path.exists():
        raise RuntimeError("Não existe catálogo AMHPDF aprovado para contingência.")
    provider_payload = json.loads(provider_path.read_text("utf-8"))
    specialty_payload = json.loads(specialty_path.read_text("utf-8"))
    providers = provider_payload.get("records", [])
    specialties = specialty_payload.get("records", [])
    if len(providers) < 10000 or not specialties:
        raise RuntimeError("O catálogo AMHPDF de contingência não atende aos limites de segurança.")
    return providers, specialties


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def write_resource(root: Path, relative: str, value):
    payload = json_bytes(value)
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return sha_bytes(payload)


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    generated_at = now.isoformat().replace("+00:00", "Z")
    verified_date = now.date().isoformat()
    config = json.loads((ROOT / "sources" / "plan-assiste.json").read_text("utf-8"))
    session = requests.Session()
    with tempfile.TemporaryDirectory(prefix="plan-assiste-build-") as temp:
        work = Path(temp)
        amhp_status = "updated"
        amhp_competence = verified_date
        try:
            providers, specialties = collect_amhp(session, verified_date)
        except Exception as exc:
            # A AMHPDF atualmente rejeita alguns endereços de datacenter (HTTP 403).
            # Nessa condição o pipeline não substitui nem esvazia a base: conserva a
            # última extração validada e torna a indisponibilidade visível no catálogo.
            providers, specialties = load_last_approved_amhp()
            amhp_status = "temporarily_unavailable"
            amhp_competence = max((item.get("verified_at") or "" for item in providers), default="") or verified_date
            print(f"Aviso: AMHPDF indisponível; última versão aprovada preservada ({exc}).", file=sys.stderr)
        remote, specialties = telemedicine_records(config, specialties, verified_date)
        procedures = collect_procedures(session, work, specialties)

        networks = list(config["networks"])
        networks.append({"network_id":"telemedicina","name":"Telemedicina Plan-Assiste","relationship":"direct_agreement","classification":"remote_care","territory":"Nacional","guide_url":config["telemedicine_url"]})
        sources = [
            {"source_id":"plan-assiste-redes","name":"Plan-Assiste — redes credenciadas","organization":"Plan-Assiste MPU","url":config["master_url"],"integration_type":"institutional_reference","frequency":"daily","last_run":generated_at,"record_count":len(networks),"status":"updated","competence":verified_date,"territorial_coverage":"Nacional"},
            {"source_id":"amhp-api","name":"AMHPDF — Encontre seu Médico","organization":"AMHPDF","url":f"{AMHP_BASE}/swagger/v1/swagger.json","integration_type":"public_api","frequency":"daily","last_run":generated_at,"record_count":len(providers),"status":amhp_status,"status_note":"Última versão aprovada preservada; nova tentativa ocorrerá na próxima execução." if amhp_status != "updated" else None,"competence":amhp_competence,"territorial_coverage":"Distrito Federal e entorno"},
            {"source_id":"plan-assiste-telemedicina","name":"Plan-Assiste — Telemedicina","organization":"Plan-Assiste MPU","url":config["telemedicine_url"],"integration_type":"institutional_reference","frequency":"daily","last_run":generated_at,"record_count":len(remote),"status":"updated","competence":verified_date,"territorial_coverage":"Nacional"},
            {"source_id":"ans-tuss","name":"TUSS 22","organization":"Agência Nacional de Saúde Suplementar","url":TUSS_SOURCE,"integration_type":"public_dataset","frequency":"weekly","last_run":generated_at,"record_count":len(procedures),"status":"updated","competence":"202609","territorial_coverage":"Nacional"},
            {"source_id":"ans-tuss-sigtap","name":"Compatibilização TUSS × SIGTAP","organization":"ANS / Ministério da Saúde","url":ANS_CROSSWALK,"integration_type":"official_crosswalk","frequency":"monthly","last_run":generated_at,"record_count":sum(1 for item in procedures if item["sigtap_codes"]),"status":"updated","competence":"201704 + SIGTAP 202609","territorial_coverage":"Nacional"}
        ]
        for source in sources:
            source["checksum"] = None

        candidate = work / "api-v2"
        envelope = lambda records: {"schema_version":SCHEMA_VERSION,"environment":"production","generated_at":generated_at,"record_count":len(records),"records":records}
        checksums = {}
        checksums["amhp"] = write_resource(candidate, "prestadores/amhp-df.json", envelope(providers))
        checksums["telemedicine"] = write_resource(candidate, "prestadores/telemedicina.json", envelope(remote))
        for filename, source_id in [("plan-assiste-direto.json","plan-assiste-direto"),("coopmed-rs.json","coopmed-rs"),("demais-fontes.json","demais-fontes")]:
            checksums[source_id] = write_resource(candidate, f"prestadores/{filename}", envelope([]))
        provider_index = {"schema_version":SCHEMA_VERSION,"generated_at":generated_at,"record_count":len(providers)+len(remote),"shards":[
            {"source_id":"amhp-api","url":"./amhp-df.json","record_count":len(providers),"checksum_sha256":checksums["amhp"]},
            {"source_id":"plan-assiste-telemedicina","url":"./telemedicina.json","record_count":len(remote),"checksum_sha256":checksums["telemedicine"]}
        ]}
        resource_hashes = {}
        resource_hashes["providers"] = write_resource(candidate, "prestadores/index.json", provider_index)
        resource_hashes["networks"] = write_resource(candidate, "redes.json", envelope(networks))
        resource_hashes["specialties"] = write_resource(candidate, "especialidades.json", envelope(specialties))
        resource_hashes["procedures"] = write_resource(candidate, "procedimentos.json", envelope(procedures))
        resource_hashes["sources"] = write_resource(candidate, "fontes.json", envelope(sources))
        search_index = [{"kind":"procedure","id":item["procedure_id"],"code":item["code"],"label":item["name"]} for item in procedures]
        search_index += [{"kind":"specialty","id":item["specialty_id"],"label":item["name"]} for item in specialties]
        write_resource(candidate, "indices/busca-geral.json", envelope(search_index))
        write_resource(candidate, "indices/procedimentos.json", {"schema_version":SCHEMA_VERSION,"generated_at":generated_at,"records":[{"procedure_id":p["procedure_id"],"related_specialty_ids":p["related_specialty_ids"]} for p in procedures if p["related_specialty_ids"]]})
        localities = sorted({(loc["address"].get("state"), loc["address"].get("city")) for item in providers for loc in item["service_locations"] if loc["address"].get("state") or loc["address"].get("city")}, key=lambda item: ((item[0] or ""), (item[1] or "")))
        write_resource(candidate, "indices/localidades.json", envelope([{"state":state,"city":city} for state,city in localities]))
        manifest = {
            "schema_version":SCHEMA_VERSION,"environment":"production","generated_at":generated_at,
            "resources":{
                "providers":{"url":"./prestadores/index.json","checksum_sha256":resource_hashes["providers"]},
                "procedures":{"url":"./procedimentos.json","checksum_sha256":resource_hashes["procedures"]},
                "networks":{"url":"./redes.json","checksum_sha256":resource_hashes["networks"]},
                "specialties":{"url":"./especialidades.json","checksum_sha256":resource_hashes["specialties"]},
                "sources":{"url":"./fontes.json","checksum_sha256":resource_hashes["sources"]}
            },
            "sources":[source["source_id"] for source in sources],"publication_status":"approved",
            "authorization":{"status":"authorized","reference":"Autorização institucional registrada; uso técnico de APIs públicas autorizado."},
            "metrics":{"providers":len(providers)+len(remote),"procedures":len(procedures),"networks":len(networks),"specialties":len(specialties)}
        }
        write_resource(candidate, "manifest.json", manifest)

        previous = None
        if (OUTPUT / "manifest.json").exists():
            previous = json.loads((OUTPUT / "manifest.json").read_text("utf-8"))
        reasons = []
        if len(providers) == 0 or len(procedures) == 0:
            reasons.append("fonte obrigatória vazia")
        if previous and not os.getenv("ALLOW_BREAKING_DATA_UPDATE"):
            old = previous.get("metrics", {}).get("providers", 0)
            if old and len(providers)+len(remote) < old * .95:
                reasons.append("remoção superior a 5% dos prestadores")
            if old and abs((len(providers)+len(remote))-old) / old > .10:
                reasons.append("variação total de prestadores superior a 10%")
        if reasons:
            report = {"generated_at":generated_at,"status":"quarantined","reasons":reasons,"candidate_metrics":manifest["metrics"],"previous_metrics":previous.get("metrics") if previous else None}
            (ROOT / "reports").mkdir(exist_ok=True)
            (ROOT / "reports" / "quarantine-latest.json").write_bytes(json_bytes(report))
            raise RuntimeError("Atualização em quarentena: " + "; ".join(reasons))
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(candidate, OUTPUT)
        print(json.dumps(manifest["metrics"], ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
