# Fontes e critérios de publicação

## AMHPDF

O adaptador usa `GET /api/Especialidades` e `GET /api/Buscar`, sempre com o parâmetro de convênio `o=639`. As consultas amplas são unidas por identificador interno, que é transformado em hash antes da publicação. Matrícula, sexo, imagens, observações e flags administrativas não são gravados.

## TUSS e SIGTAP

A relação publicada segue esta cadeia:

1. procedimento TUSS 22 vigente;
2. compatibilização TUSS×SIGTAP oficial;
3. procedimento SIGTAP vigente;
4. relação SIGTAP procedimento×CBO;
5. normalização conservadora do título do CBO para especialidade.

Um procedimento só recebe especialidades quando toda a cadeia existe. A competência de cada tabela é preservada. A compatibilização oficial disponível é de 201704; por isso o processo confirma a existência dos códigos nas tabelas 202609 antes de publicar a relação.

## Rede Plan-Assiste

A página institucional de rede credenciada controla quais redes podem ser apresentadas como vinculadas ao Plan-Assiste. Nenhuma API externa cria vínculo por conta própria.

## Limites

Credenciamento, execução do procedimento, cobertura, autorização, elegibilidade e disponibilidade são conceitos separados. A pesquisa por procedimento indica especialidades relacionadas e exige confirmação nos canais oficiais.

