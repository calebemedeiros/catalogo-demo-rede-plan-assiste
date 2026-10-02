import { createHash } from "node:crypto";
import { mkdir, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiDir = path.join(root, "api", "v1");
const sourcesDir = path.join(apiDir, "fontes");
const modelsDir = path.join(root, "modelos");
const generatedAt = "2026-10-02T22:00:00Z";

await rm(sourcesDir, { recursive: true, force: true });
await mkdir(sourcesDir, { recursive: true });
await mkdir(modelsDir, { recursive: true });

const specialties = [
  "Alergia e imunologia", "Anestesiologia", "Angiologia", "Cardiologia",
  "Cirurgia cardiovascular", "Cirurgia geral", "Cirurgia pediátrica", "Clínica médica",
  "Coloproctologia", "Dermatologia", "Endocrinologia", "Endoscopia",
  "Gastroenterologia", "Genética médica", "Geriatria", "Ginecologia",
  "Hematologia", "Infectologia", "Mastologia", "Medicina de família",
  "Medicina do trabalho", "Medicina esportiva", "Nefrologia", "Neurocirurgia",
  "Neurologia", "Nutrologia", "Obstetrícia", "Oftalmologia", "Oncologia clínica",
  "Ortopedia", "Otorrinolaringologia", "Patologia", "Pediatria", "Pneumologia",
  "Psiquiatria", "Radiologia", "Reumatologia", "Urologia", "Medicina intensiva",
  "Psicologia", "Fisioterapia", "Nutrição", "Odontologia", "Fonoaudiologia",
  "Terapia ocupacional", "Enfermagem", "Serviço social"
];

const nationalLocations = [
  { city: "Rio Branco", state: "AC", district: "Centro", ddd: "68" },
  { city: "Manaus", state: "AM", district: "Adrianópolis", ddd: "92" },
  { city: "Belém", state: "PA", district: "Umarizal", ddd: "91" },
  { city: "Porto Velho", state: "RO", district: "Olaria", ddd: "69" },
  { city: "Palmas", state: "TO", district: "Plano Diretor Sul", ddd: "63" },
  { city: "São Luís", state: "MA", district: "Renascença", ddd: "98" },
  { city: "Fortaleza", state: "CE", district: "Aldeota", ddd: "85" },
  { city: "Natal", state: "RN", district: "Tirol", ddd: "84" },
  { city: "Recife", state: "PE", district: "Boa Viagem", ddd: "81" },
  { city: "Salvador", state: "BA", district: "Pituba", ddd: "71" },
  { city: "Brasília", state: "DF", district: "Asa Norte", ddd: "61" },
  { city: "Goiânia", state: "GO", district: "Setor Bueno", ddd: "62" },
  { city: "Cuiabá", state: "MT", district: "Centro Sul", ddd: "65" },
  { city: "Campo Grande", state: "MS", district: "Jardim dos Estados", ddd: "67" },
  { city: "Belo Horizonte", state: "MG", district: "Funcionários", ddd: "31" },
  { city: "Vitória", state: "ES", district: "Praia do Canto", ddd: "27" },
  { city: "Rio de Janeiro", state: "RJ", district: "Botafogo", ddd: "21" },
  { city: "São Paulo", state: "SP", district: "Bela Vista", ddd: "11" },
  { city: "Curitiba", state: "PR", district: "Batel", ddd: "41" },
  { city: "Porto Alegre", state: "RS", district: "Moinhos de Vento", ddd: "51" }
];

const dfDistricts = [
  "Águas Claras", "Asa Norte", "Asa Sul", "Ceilândia", "Gama", "Guará",
  "Lago Norte", "Lago Sul", "Núcleo Bandeirante", "Paranoá", "Planaltina",
  "Recanto das Emas", "Samambaia", "Santa Maria", "São Sebastião", "Sobradinho",
  "Sudoeste", "Taguatinga", "Vicente Pires", "Riacho Fundo"
];

const spLocations = [
  "São Paulo", "Campinas", "Santos", "Sorocaba", "Ribeirão Preto",
  "São José dos Campos", "Bauru", "Jundiaí", "São José do Rio Preto", "Piracicaba"
].map((city, index) => ({ city, state: "SP", district: `Bairro demonstrativo ${index + 1}`, ddd: index < 5 ? "11" : "19" }));

const pad = (value, size = 3) => String(value).padStart(size, "0");

const sourceDefinitions = [
  { id: "amhpdf-demo", name: "AMHPDF — amostra demonstrativa", kind: "partner-network", relationship_label: "Rede parceira", coverage_scope: "regional", states: ["DF"] },
  { id: "plan-assiste-direto-demo", name: "Plan-Assiste — credenciamento direto demonstrativo", kind: "direct-network", relationship_label: "Credenciamento direto", coverage_scope: "national", states: nationalLocations.map((item) => item.state) },
  { id: "cnu-demo", name: "CNU — cobertura demonstrativa", kind: "cooperative-network", relationship_label: "Rede conveniada", coverage_scope: "national", states: nationalLocations.map((item) => item.state) },
  { id: "fesp-demo", name: "FESP — cobertura demonstrativa", kind: "cooperative-network", relationship_label: "Rede conveniada", coverage_scope: "regional", states: ["SP"] },
  { id: "unimeds-demo", name: "Unimeds regionais — cobertura demonstrativa", kind: "cooperative-network", relationship_label: "Intercâmbio regional", coverage_scope: "national", states: nationalLocations.map((item) => item.state) },
  { id: "rede-dor-demo", name: "Rede D'Or — cobertura demonstrativa", kind: "hospital-network", relationship_label: "Rede hospitalar", coverage_scope: "national", states: ["BA", "DF", "MG", "PE", "RJ", "SP"] }
];

const accessText = "Atendimento sujeito à elegibilidade, autorização, disponibilidade e confirmação nos canais oficiais.";

function networkLink(source) {
  return {
    source_id: source.id,
    relationship_type: source.kind,
    relationship_label: source.relationship_label,
    coverage_scope: source.coverage_scope,
    access_mode: source.kind === "direct-network" ? "Credenciamento direto" : "Rede conveniada",
    verification_required: true,
    availability_notice: accessText
  };
}

function locationFor(location, sequence, facilityPrefix = "Unidade Assistencial") {
  return {
    facility_public_id: `unidade-demo-${location.state.toLowerCase()}-${pad(sequence, 4)}`,
    facility_name: `${facilityPrefix} Demonstrativa ${location.city}`,
    phones: [`(${location.ddd}) 0000-${pad(sequence % 100, 2)}01`],
    address: {
      street: `Endereço exclusivamente demonstrativo ${pad(sequence, 4)}`,
      district: location.district,
      city: location.city,
      state: location.state
    }
  };
}

function professionalRecord({ source, number, location, namePrefix = "Profissional", specialtyOffset = 0 }) {
  const specialty = specialties[(number - 1 + specialtyOffset) % specialties.length];
  return {
    public_id: `profissional-${source.id}-${pad(number)}`,
    source_id: source.id,
    type: "professional",
    display_name: `${namePrefix} demonstrativo ${pad(number)}`,
    professional_registry: { council: specialty === "Psicologia" ? "CRP" : "CRM", state: location.state, number: `DEMO-${pad(number, 5)}` },
    specialties: [{ name: specialty, rqe: `DEMO-RQE-${pad(number, 4)}` }],
    service_locations: [locationFor(location, number)],
    network_links: [networkLink(source)],
    source_updated_at: generatedAt
  };
}

function facilityRecord({ source, number, location, namePrefix = "Hospital" }) {
  return {
    public_id: `estabelecimento-${source.id}-${pad(number)}`,
    source_id: source.id,
    type: "facility",
    display_name: `${namePrefix} demonstrativo ${location.city} ${pad(number)}`,
    professional_registry: null,
    specialties: [0, 7, 28].map((offset) => ({ name: specialties[(number + offset) % specialties.length], rqe: null })),
    service_locations: [locationFor(location, number, namePrefix)],
    network_links: [networkLink(source)],
    source_updated_at: generatedAt
  };
}

const amhpSource = sourceDefinitions[0];
const amhpRecords = Array.from({ length: 300 }, (_, index) => {
  const location = { city: "Brasília", state: "DF", district: dfDistricts[index % dfDistricts.length], ddd: "61" };
  return professionalRecord({ source: amhpSource, number: index + 1, location, namePrefix: "Médico AMHPDF" });
});

const sourceLocations = {
  "plan-assiste-direto-demo": nationalLocations,
  "cnu-demo": nationalLocations,
  "fesp-demo": spLocations,
  "unimeds-demo": [...nationalLocations].reverse(),
  "rede-dor-demo": nationalLocations.filter((item) => ["BA", "DF", "MG", "PE", "RJ", "SP"].includes(item.state))
};

const otherRecords = sourceDefinitions.slice(1).flatMap((source, sourceIndex) => {
  const locations = sourceLocations[source.id];
  const professionals = Array.from({ length: 40 }, (_, index) => professionalRecord({
    source,
    number: index + 1,
    location: locations[index % locations.length],
    namePrefix: source.kind === "hospital-network" ? "Especialista hospitalar" : "Profissional",
    specialtyOffset: (sourceIndex + 1) * 5
  }));
  const facilities = Array.from({ length: 20 }, (_, index) => facilityRecord({
    source,
    number: index + 1,
    location: locations[index % locations.length],
    namePrefix: source.kind === "hospital-network" ? "Hospital de rede" : "Unidade assistencial"
  }));
  return [...professionals, ...facilities];
});

const records = [...amhpRecords, ...otherRecords];
for (const source of sourceDefinitions) {
  source.record_count = records.filter((record) => record.source_id === source.id).length;
  source.status = "synthetic-demo";
  source.verification_notice = accessText;
}

const catalog = {
  schema_version: "3.0.0",
  environment: "demo",
  generated_at: generatedAt,
  expires_at: "2027-01-31T23:59:59Z",
  source: {
    name: "Catálogo nacional multifonte demonstrativo Plan-Assiste",
    public_url: "https://github.com/calebemedeiros/catalogo-demo-rede-plan-assiste",
    plan_name: "PLAN-ASSISTE MPU — referência demonstrativa"
  },
  authorization: { status: "synthetic-demo", reference: null },
  notices: {
    synthetic_data: true,
    eligibility: accessText,
    official_status: "Esta demonstração não representa a rede oficial ou garantia de cobertura."
  },
  sources: sourceDefinitions,
  record_count: records.length,
  records
};

const catalogText = `${JSON.stringify(catalog, null, 2)}\n`;
const checksum = createHash("sha256").update(catalogText).digest("hex");
const manifest = {
  schema_version: "3.0.0",
  environment: "demo",
  generated_at: generatedAt,
  catalog_url: "./prestadores.json",
  record_count: catalog.record_count,
  source_count: sourceDefinitions.length,
  checksum_sha256: checksum,
  authorization: { status: "synthetic-demo", reference: null }
};

function sourceFile(definition) {
  const sourceRecords = records.filter((record) => record.source_id === definition.id);
  return {
    schema_version: "3.0.0",
    environment: "demo",
    generated_at: generatedAt,
    authorization: { status: "synthetic-demo", reference: null },
    source: definition,
    record_count: sourceRecords.length,
    records: sourceRecords
  };
}

await Promise.all([
  writeFile(path.join(apiDir, "prestadores.json"), catalogText, "utf8"),
  writeFile(path.join(apiDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8"),
  ...sourceDefinitions.map((source) => writeFile(path.join(sourcesDir, `${source.id}.json`), `${JSON.stringify(sourceFile(source), null, 2)}\n`, "utf8")),
  writeFile(
    path.join(modelsDir, "modelo-importacao.csv"),
    "source_id;relationship_type;type;display_name;council;registry_state;registry_number;specialty;rqe;facility_name;phone;street;district;city;state;source_updated_at\n" +
      "nova-fonte-demo;partner-network;professional;Prestador demonstrativo;CRM;DF;DEMO-00001;Especialidade demonstrativa;;Unidade Modelo;(61) 0000-0000;Endereço demonstrativo;Asa Sul;Brasília;DF;2026-10-02T22:00:00Z\n",
    "utf8"
  )
]);

console.log(`Gerados ${catalog.record_count} registros sintéticos em ${sourceDefinitions.length} fontes nacionais e regionais.`);
console.log(`SHA-256: ${checksum}`);
