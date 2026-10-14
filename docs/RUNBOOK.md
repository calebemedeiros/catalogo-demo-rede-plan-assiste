# Operação e publicação

## Execução normal

O workflow executa uma leitura de cada endpoint configurado, gera `dist/api/v2`, valida o contrato `4.1.0`, empacota e publica o diretório `dist` pelo GitHub Pages.

## Fonte indisponível

Não altere headers para imitar clientes, não use proxy e não crie consultas alternativas. Verifique a documentação pública e registre a fonte como `unavailable` ou `guide_only`.

## Inclusão de fonte

Uma nova fonte exige URL HTTPS oficial, resposta JSON, documentação do método e evidência de vínculo com o Plan-Assiste. Antes da ativação, inclua host na lista positiva, esquema mínimo, teste de campos proibidos e comportamento de falha.

## Rollback

O deploy é atômico. Para restaurar uma versão, utilize o artefato de uma execução aprovada do GitHub Actions. JSONs gerados não são versionados na branch.
