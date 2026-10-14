# Como configurar uma API pública

1. Abra `sources/catalog-sources.toml`.
2. Descomente um dos blocos de exemplo.
3. Escolha `direct_agreement` ou `indirect_agreement`.
4. Informe a URL pública, documentação, caminho da lista JSON e guia oficial.
5. Mapeie os nomes dos campos da resposta para os campos públicos do catálogo.
6. Registre a autorização sem inserir nomes ou dados pessoais.
7. Execute coleta, validação e empacotamento.
8. Revise somente o JSON minimizado em `dist/api/v2`.

Os campos `public_id` e `display_name` são obrigatórios. Os demais são opcionais e somente aparecem quando forem explicitamente mapeados.
