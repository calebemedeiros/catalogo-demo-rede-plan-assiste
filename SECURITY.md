# Segurança do catálogo

O pipeline processa somente fontes públicas autorizadas e publica uma lista positiva de campos. Dados brutos são mantidos em diretório temporário e eliminados ao final.

## Dados proibidos

- dados de beneficiários, CPF e carteirinha;
- histórico de pesquisa ou informação clínica;
- matrícula e identificadores administrativos da fonte;
- imagens, observações internas, sexo e flags operacionais;
- credenciais, tokens e chaves no repositório ou frontend.

## Controles

- identificadores públicos derivados por SHA-256;
- deduplicação e validação de vínculos;
- lista positiva de domínios para links;
- checksums do manifesto, recursos e fragmentos;
- falha para fontes vazias e quarentena para variações anormais;
- dependências fixadas, SBOM e artefatos versionados;
- permissões mínimas no workflow;
- publicação somente depois dos testes.

Não inclua dados completos da fonte em issues ou logs. Relatórios de falha devem conter somente métricas e identificadores técnicos.
