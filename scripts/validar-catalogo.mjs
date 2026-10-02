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
const amhp = await readJson(path.join(apiDir, "fontes", "amhpdf-demo.json"));
const direct = await readJson(path.join(apiDir, "fontes", "plan-assiste-demo.json"));

assert(manifest.schema_version === "2.0.0", "Versão inesperada do manifesto.");
assert(catalog.schema_version === "2.0.0", "Versão inesperada do catálogo.");
assert(manifest.environment === "demo" && catalog.environment === "demo", "Apenas ambiente demo é permitido.");
assert(manifest.authorization?.status === "synthetic-demo", "Manifesto sem marcação sintética.");
assert(catalog.authorization?.status === "synthetic-demo", "Catálogo sem marcação sintética.");
assert(manifest.authorization.reference === null, "Demonstração não pode simular autorização real.");
assert(Array.isArray(catalog.records) && catalog.records.length === 360, "O catálogo deve conter exatamente 360 registros.");
assert(catalog.record_count === 360 && manifest.record_count === 360, "Contagens do catálogo divergentes.");
assert(Array.isArray(catalog.sources) && catalog.sources.length === 2, "Duas fontes demonstrativas são esperadas.");

const calculatedHash = createHash("sha256").update(catalogBuffer).digest("hex");
assert(calculatedHash === manifest.checksum_sha256, "Checksum SHA-256 divergente.");

const amhpRecords = catalog.records.filter((record) => record.source_id === "amhpdf-demo");
const directRecords = catalog.records.filter((record) => record.source_id === "plan-assiste-direto-demo");
assert(amhpRecords.length === 300, "A fonte AMHPDF demonstrativa deve ter 300 médicos.");
assert(amhpRecords.every((record) => record.type === "professional" && record.professional_registry?.council === "CRM"), "Amostra AMHPDF contém registro médico inválido.");
assert(directRecords.length === 60, "A fonte direta demonstrativa deve ter 60 registros.");
assert(directRecords.filter((record) => record.type === "professional").length === 40, "São esperados 40 profissionais diretos.");
assert(directRecords.filter((record) => record.type === "facility").length === 20, "São esperados 20 estabelecimentos.");
assert(amhp.record_count === 300 && amhp.records.length === 300, "Arquivo de fonte AMHPDF inconsistente.");
assert(direct.record_count === 60 && direct.records.length === 60, "Arquivo de fonte direta inconsistente.");

const forbiddenKeys = new Set([
  "associadoId", "matricula", "pessoaFJ", "sexo", "marqueAqui", "atendimento",
  "tea", "observacao", "imagem1", "imagem2", "imagem3", "imagem4", "imagem5"
]);
const identifiers = new Set();

const walk = (value, currentPath = "catalog") => {
  if (Array.isArray(value)) return value.forEach((item, index) => walk(item, `${currentPath}[${index}]`));
  if (!value || typeof value !== "object") return;
  for (const [key, item] of Object.entries(value)) {
    assert(!forbiddenKeys.has(key), `Campo proibido em ${currentPath}.${key}.`);
    walk(item, `${currentPath}.${key}`);
  }
};
walk(catalog);

for (const record of catalog.records) {
  assert(!identifiers.has(record.public_id), `Identificador duplicado: ${record.public_id}.`);
  identifiers.add(record.public_id);
  assert(["professional", "facility"].includes(record.type), `Tipo inválido: ${record.public_id}.`);
  assert(/demonstrativo|modelo/i.test(record.display_name), `Registro sem marcação sintética: ${record.public_id}.`);
  assert(record.professional_registry?.number?.startsWith("DEMO-") || record.professional_registry === null, `Registro profissional não sintético: ${record.public_id}.`);
  assert(record.service_locations.every((location) => location.phones.every((phone) => phone.includes("0000-"))), `Telefone não sintético: ${record.public_id}.`);
}

console.log("Catálogo válido: 360 registros sintéticos, 2 fontes, checksum confirmado e nenhum campo proibido.");
