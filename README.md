# Catálogo configurável da Rede Assistencial

Estrutura vazia para a equipe responsável configurar APIs públicas de credenciados diretos e indiretos. O repositório não contém prestadores, redes, especialidades, procedimentos, URLs institucionais nem respostas reais de APIs.

## Configuração

Edite `sources/catalog-sources.toml`. O arquivo contém apenas blocos comentados com os campos necessários para:

- fonte de credenciamento direto;
- fonte de credenciamento indireto;
- URL pública da API e documentação;
- caminho da lista na resposta JSON;
- mapeamento dos campos permitidos.

Somente depois da validação institucional, altere `authorization.status` para `authorized` e preencha uma referência interna sem dados pessoais.

## Processamento

```powershell
python -m pip install -r requirements.txt
python scripts/build_production.py
python scripts/validate_production.py
python scripts/package_release.py
```

O coletor executa uma leitura `GET`, valida JSON, seleciona somente os campos mapeados e grava a saída em `dist/api/v2`. Ele não usa credenciais, não enumera consultas, não segue rotas alternativas e não preserva a resposta bruta.

O GitHub Actions publica apenas `dist` como artefato do GitHub Pages. Nenhum JSON gerado é gravado automaticamente na branch.
