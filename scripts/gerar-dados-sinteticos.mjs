import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const apiDir = path.join(root, "api", "v1");
const sourcesDir = path.join(apiDir, "fontes");
const modelsDir = path.join(root, "modelos");
const generatedAt = "2026-10-02T21:00:00Z";

await mkdir(sourcesDir, { recursive: true });
await mkdir(modelsDir, { recursive: true });

const medicalSpecialties = [
  "Alergia e imunologia", "Anestesiologia", "Angiologia", "Cardiologia",
  "Cirurgia cardiovascular", "Cirurgia geral", "Cirurgia pediátrica", "Clínica médica",
  "Coloproctologia", "Dermatologia", "Endocrinologia", "Endoscopia",
  "Gastroenterologia", "Genética médica", "Geriatria", "Ginecologia",
  "Hematologia", "Homeopatia", "Infectologia", "Mastologia",
  "Medicina de família", "Medicina do trabalho", "Medicina esportiva", "Nefrologia",
  "Neurocirurgia", "Neurologia", "Nutrologia", "Obstetrícia",
  "Oftalmologia", "Oncologia clínica", "Ortopedia", "Otorrinolaringologia",
  "Patologia", "Pediatria", "Pneumologia", "Psiquiatria",
  "Radiologia", "Reumatologia", "Urologia", "Medicina intensiva"
];

const districts = [
  "Águas Claras", "Asa Norte", "Asa Sul", "Ceilândia", "Gama",
  "Guará", "Lago Norte", "Lago Sul", "Núcleo Bandeirante", "Paranoá",
  "Planaltina", "Recanto das Emas", "Samambaia", "Santa Maria", "São Sebastião",
  "Sobradinho", "Sudoeste", "Taguatinga", "Vicente Pires", "Riacho Fundo"
];

const facilityNames = districts.map((district, index) =>
  index % 4 === 0
    ? `Hospital Modelo ${district}`
    : index % 4 === 1
      ? `Centro Clínico Modelo ${district}`
      : index % 4 === 2
        ? `Unidade Assistencial Modelo ${district}`
        : `Instituto de Saúde Modelo ${district}`
);

const pad = (value, size = 3) => String(value).padStart(size, "0");

const addressFor = (index) => ({
  street: `Endereço exclusivamente demonstrativo ${pad(index + 1)}`,
  district: districts[index],
  city: "Brasília",
  state: "DF"
});

const locationFor = (index, phoneSuffix = 0) => ({
  facility_public_id: `estabelecimento-demo-${pad(index + 1)}`,
  facility_name: facilityNames[index],
  phones: [`(61) 0000-${pad(index + 1, 2)}${pad(phoneSuffix + 1, 2)}`],
  address: addressFor(index)
});

const amhpRecords = Array.from({ length: 300 }, (_, offset) => {
  const number = offset + 1;
  const specialtyIndex = offset % medicalSpecialties.length;
  const locations = [locationFor(offset % districts.length, offset % 9)];
  if (number % 5 === 0) locations.push(locationFor((offset + 7) % districts.length, (offset + 2) % 9));
  const specialties = [{
    name: medicalSpecialties[specialtyIndex],
    rqe: `DEMO-RQE-${pad(number, 4)}`
  }];
  if (number % 6 === 0) {
    specialties.push({
      name: medicalSpecialties[(specialtyIndex + 9) % medicalSpecialties.length],
      rqe: `DEMO-RQE-${pad(number + 500, 4)}`
    });
  }
  return {
    public_id: `profissional-amhpdf-demo-${pad(number)}`,
    source_id: "amhpdf-demo",
    type: "professional",
    display_name: `Médico AMHPDF demonstrativo ${pad(number)}`,
    professional_registry: { council: "CRM", state: "DF", number: `DEMO-${pad(number, 5)}` },
    specialties,
    service_locations: locations,
    source_updated_at: generatedAt
  };
});

const directProfiles = [
  { specialty: "Psicologia", council: "CRP" },
  { specialty: "Fisioterapia", council: "CREFITO" },
  { specialty: "Nutrição", council: "CRN" },
  { specialty: "Odontologia", council: "CRO" },
  { specialty: "Fonoaudiologia", council: "CREFONO" },
  { specialty: "Terapia ocupacional", council: "CREFITO" },
  { specialty: "Enfermagem", council: "COREN" },
  { specialty: "Serviço social", council: "CRESS" }
];

const directProfessionals = Array.from({ length: 40 }, (_, offset) => {
  const number = offset + 1;
  const profile = directProfiles[offset % directProfiles.length];
  return {
    public_id: `profissional-plan-assiste-demo-${pad(number)}`,
    source_id: "plan-assiste-direto-demo",
    type: "professional",
    display_name: `Prestador Plan-Assiste demonstrativo ${pad(number)}`,
    professional_registry: { council: profile.council, state: "DF", number: `DEMO-${pad(number, 5)}` },
    specialties: [{ name: profile.specialty, rqe: null }],
    service_locations: [locationFor((offset * 3) % districts.length, (offset + 4) % 9)],
    source_updated_at: generatedAt
  };
});

const facilitySpecialties = [
  ["Cardiologia", "Clínica médica", "Radiologia"],
  ["Pediatria", "Ginecologia", "Obstetrícia"],
  ["Ortopedia", "Fisioterapia", "Medicina esportiva"],
  ["Oftalmologia", "Otorrinolaringologia", "Fonoaudiologia"],
  ["Psicologia", "Psiquiatria", "Terapia ocupacional"]
];

const facilities = Array.from({ length: 20 }, (_, offset) => ({
  public_id: `estabelecimento-demo-${pad(offset + 1)}`,
  source_id: "plan-assiste-direto-demo",
  type: "facility",
  display_name: facilityNames[offset],
  professional_registry: null,
  specialties: facilitySpecialties[offset % facilitySpecialties.length].map((name) => ({ name, rqe: null })),
  service_locations: [locationFor(offset, 0)],
  source_updated_at: generatedAt
}));

const sourceDefinitions = [
  {
    id: "amhpdf-demo",
    name: "AMHPDF — amostra demonstrativa",
    kind: "partner-network",
    status: "synthetic-demo",
    record_count: amhpRecords.length
  },
  {
    id: "plan-assiste-direto-demo",
    name: "Plan-Assiste — credenciamento direto demonstrativo",
    kind: "direct-network",
    status: "synthetic-demo",
    record_count: directProfessionals.length + facilities.length
  }
];

const catalog = {
  schema_version: "2.0.0",
  environment: "demo",
  generated_at: generatedAt,
  expires_at: "2027-01-31T23:59:59Z",
  source: {
    name: "Catálogo integrado demonstrativo Plan-Assiste",
    public_url: "https://github.com/calebemedeiros/catalogo-demo-rede-plan-assiste",
    plan_id: 639,
    plan_name: "PLAN ASSISTE (MPU) — referência demonstrativa"
  },
  authorization: { status: "synthetic-demo", reference: null },
  sources: sourceDefinitions,
  record_count: amhpRecords.length + directProfessionals.length + facilities.length,
  records: [...amhpRecords, ...directProfessionals, ...facilities]
};

const catalogText = `${JSON.stringify(catalog, null, 2)}\n`;
const checksum = createHash("sha256").update(catalogText).digest("hex");
const manifest = {
  schema_version: "2.0.0",
  environment: "demo",
  generated_at: generatedAt,
  catalog_url: "./prestadores.json",
  record_count: catalog.record_count,
  source_count: sourceDefinitions.length,
  checksum_sha256: checksum,
  authorization: { status: "synthetic-demo", reference: null }
};

const sourceFile = (definition, records) => ({
  schema_version: "2.0.0",
  environment: "demo",
  generated_at: generatedAt,
  authorization: { status: "synthetic-demo", reference: null },
  source: definition,
  record_count: records.length,
  records
});

await Promise.all([
  writeFile(path.join(apiDir, "prestadores.json"), catalogText, "utf8"),
  writeFile(path.join(apiDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8"),
  writeFile(path.join(sourcesDir, "amhpdf-demo.json"), `${JSON.stringify(sourceFile(sourceDefinitions[0], amhpRecords), null, 2)}\n`, "utf8"),
  writeFile(path.join(sourcesDir, "plan-assiste-demo.json"), `${JSON.stringify(sourceFile(sourceDefinitions[1], [...directProfessionals, ...facilities]), null, 2)}\n`, "utf8"),
  writeFile(
    path.join(modelsDir, "modelo-importacao.csv"),
    "source_id;type;display_name;council;state;registry_number;specialty;rqe;facility_name;phone;street;district;city;state_address\n" +
      "nova-fonte-demo;professional;Prestador demonstrativo;CONSELHO;DF;DEMO-00001;Especialidade demonstrativa;;Unidade Modelo;(61) 0000-0000;Endereço demonstrativo;Asa Sul;Brasília;DF\n",
    "utf8"
  )
]);

console.log(`Gerados ${catalog.record_count} registros sintéticos em ${sourceDefinitions.length} fontes.`);
console.log(`SHA-256: ${checksum}`);
