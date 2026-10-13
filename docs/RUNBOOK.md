# Operação, publicação e rollback

## Publicação normal

O workflow coleta, valida, empacota e publica. Se todos os testes passarem, o GitHub Pages recebe `api/v2`. Cada execução aprovada gera um artefato com retenção de 90 dias.

## Quarentena

Falhas interrompem o job antes do deploy. O relatório local fica em `reports/quarantine-latest.json`. Issues ou logs devem conter apenas métricas e identificadores técnicos, nunca o conteúdo completo da fonte.

## Aprovação de variação esperada

1. revise a origem, o esquema, as contagens e uma amostra;
2. registre a justificativa na revisão;
3. execute manualmente com a opção de liberar a variação;
4. valide o pacote e publique uma nova versão.

## Rollback

Baixe o artefato da última execução aprovada e publique seu conteúdo. Como o deploy só acontece depois da validação, uma coleta recusada não substitui a versão anterior.

