# Catálogo da Rede Assistencial do Plan-Assiste

Pipeline que coleta fontes públicas autorizadas, aplica lista positiva de campos, normaliza vínculos e gera a API estática consumida pelo Painel Nacional da Rede Assistencial.

O catálogo sintético anterior permanece isolado em `api/v1`. A versão de produção usa `api/v2` e contrato `4.0.0`.

## Fontes da versão candidata

- AMHPDF, convênio `639`, por API pública;
- cadastro mestre de redes e telemedicina no portal do Plan-Assiste;
- TUSS 22, competência 202609;
- compatibilização oficial TUSS×SIGTAP publicada pela ANS;
- SIGTAP 202609, incluindo procedimento×CBO.

Redes sem API pública estável são publicadas como diretório e apontam para o guia oficial. O catálogo não afirma que essas listas estão integralmente incorporadas.

## Execução

```powershell
python -m pip install -r requirements.txt
python scripts/build_production.py
python scripts/validate_production.py
python scripts/package_release.py
```

O coletor grava somente os campos públicos permitidos. Arquivos brutos ficam em diretório temporário e são eliminados ao final.

## Quarentena

A geração é interrompida quando uma fonte obrigatória fica vazia, quando o volume cai mais de 5% ou varia mais de 10%, quando há campos proibidos, vínculos inválidos, duplicidades ou checksum divergente. A publicação anterior permanece ativa. Uma exceção revisada exige execução manual com `ALLOW_BREAKING_DATA_UPDATE=1`.

## Entrega

`python scripts/package_release.py` cria o ZIP, `SHA256SUMS.txt` e SBOM CycloneDX em `release/`. As últimas execuções aprovadas ficam preservadas como artefatos do GitHub Actions.

Consulte [fontes e critérios](docs/FONTES_E_CRITERIOS.md), [operação e rollback](docs/RUNBOOK.md) e [segurança](SECURITY.md).
