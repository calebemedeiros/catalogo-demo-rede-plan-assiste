import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiDir = path.join(root, "api", "v1");
const readJson = async (file) => JSON.parse(await readFile(file, "utf8"));
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const manifest = await readJson(path.join(apiDir, "manifest.json"));
const catalogBuffer = await readFile(path.join(apiDir, "prestadores.json"));
const catalog = JSON.parse(catalogBuffer.toString("utf8"));

assert(manifest.schema_version === "3.0.0", "Versão inesperada do manifesto.");
assert(catalog.schema_version === "3.0.0", "Versão inesperada do catálogo.");
assert(manifest.environment === "demo" && catalog.environment === "demo", "Apenas ambiente demo é permitido.");
assert(manifest.authorization?.status === "synthetic-demo", "Manifesto sem marcação sintética.");
assert(catalog.authorization?.status === "synthetic-demo", "Catálogo sem marcação sintética.");
assert(manifest.authorization.reference === null, "Demonstração não pode simular autorização real.");
assert(catalog.notices?.synthetic_data === true, "Aviso de dados sintéticos ausente.");
assert(Array.isArray(catalog.records) && catalog.records.length === 600, "O catálogo nacional deve conter exatamente 600 registros.");
assert(catalog.record_count === 600 && manifest.record_count === 600, "Contagens do catálogo divergentes.");
assert(Array.isArray(catalog.sources) && catalog.sources.length === 6, "Seis fontes demonstrativas são esperadas.");
assert(manifest.source_count === 6, "Quantidade de fontes divergente no manifesto.");

const calculatedHash = createHash("sha256").update(catalogBuffer).digest("hex");
assert(calculatedHash === manifest.checksum_sha256, "Checksum SHA-256 divergente.");

const expectedCounts = {
  "amhpdf-demo": 300,
  "plan-assiste-direto-demo": 60,
  "cnu-demo": 60,
  "fesp-demo": 60,
  "unimeds-demo": 60,
  "rede-dor-demo": 60
};

for (const [sourceId, expected] of Object.entries(expectedCounts)) {
  const source = catalog.sources.find((item) => item.id === sourceId);
  const sourceRecords = catalog.records.filter((record) => record.source_id === sourceId);
  assert(source?.record_count === expected, `Contagem inválida para ${sourceId}.`);
  assert(sourceRecords.length === expected, `Registros inválidos para ${sourceId}.`);
  const sourceFile = await readJson(path.join(apiDir, "fontes", `${sourceId}.json`));
  assert(sourceFile.schema_version === "3.0.0" && sourceFile.record_count === expected, `Arquivo de fonte inconsistente: ${sourceId}.`);
}

const forbiddenKeys = new Set([
  "associadoId", "matricula", "pessoaFJ", "sexo", "marqueAqui", "atendimento",
  "tea", "observacao", "imagem1", "imagem2", "imagem3", "imagem4", "imagem5"
]);
const sourceIds = new Set(catalog.sources.map((source) => source.id));
const identifiers = new Set();

function walk(value, currentPath = "catalog") {
  if (Array.isArray(value)) return value.forEach((item, index) => walk(item, `${currentPath}[${index}]`));
  if (!value || typeof value !== "object") return;
  for (const [key, item] of Object.entries(value)) {
    assert(!forbiddenKeys.has(key), `Campo proibido em ${currentPath}.${key}.`);
    walk(item, `${currentPath}.${key}`);
  }
}
walk(catalog);

for (const record of catalog.records) {
  assert(!identifiers.has(record.public_id), `Identificador duplicado: ${record.public_id}.`);
  identifiers.add(record.public_id);
  assert(sourceIds.has(record.source_id), `Fonte inexistente: ${record.public_id}.`);
  assert(["professional", "facility"].includes(record.type), `Tipo inválido: ${record.public_id}.`);
  assert(/demonstrativ/i.test(record.display_name), `Registro sem marcação sintética: ${record.public_id}.`);
  assert(Array.isArray(record.network_links) && record.network_links.length > 0, `Vínculo de rede ausente: ${record.public_id}.`);
  assert(record.network_links.every((link) => sourceIds.has(link.source_id) && link.verification_required === true), `Vínculo de rede inválido: ${record.public_id}.`);
  assert(record.professional_registry?.number?.startsWith("DEMO-") || record.professional_registry === null, `Registro profissional não sintético: ${record.public_id}.`);
  assert(record.service_locations.every((location) =>
    /^[A-Z]{2}$/.test(location.address.state) &&
    Boolean(location.address.city) &&
    location.phones.every((phone) => phone.includes("0000-"))
  ), `Localização ou telefone inválido: ${record.public_id}.`);
}

const states = new Set(catalog.records.flatMap((record) => record.service_locations.map((location) => location.address.state)));
assert(states.size >= 20, "A demonstração nacional deve representar pelo menos 20 UFs.");

console.log(`Catálogo válido: 600 registros sintéticos, 6 fontes, ${states.size} UFs, checksum confirmado e nenhum campo proibido.`);
