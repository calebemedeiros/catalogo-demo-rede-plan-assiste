# Como adicionar uma fonte de prestadores

## Fluxo demonstrado

O catálogo consolida fontes distintas em um único contrato:

```text
arquivo da fonte
      ↓
normalização
      ↓
validação de campos e origem
      ↓
deduplicação
      ↓
prestadores.json
      ↓
manifest.json atualizado por último
```

## Arquivo de entrada

O diretório `modelos` contém um CSV de referência. Cada registro deve indicar, no mínimo:

- `source_id`;
- tipo de prestador;
- nome de divulgação;
- conselho e registro, quando aplicáveis;
- especialidade;
- estabelecimento;
- telefone profissional;
- endereço profissional.

## Regras para uma fonte real

Antes de aceitar uma base real, deverão existir:

1. autorização escrita para uso e publicação;
2. responsável institucional pela fonte;
3. finalidade e campos aprovados;
4. canal de correção e exclusão;
5. periodicidade de atualização;
6. regras de retenção e revogação;
7. testes contra publicação de campos administrativos;
8. ambiente de armazenamento institucional ou formalmente aprovado.

## Inclusão pelo Plan-Assiste

Uma base própria do Plan-Assiste poderá ser adicionada como nova fonte sem alterar a interface. O processo recomendado é:

1. preencher o modelo aprovado ou fornecer exportação equivalente;
2. executar o normalizador em ambiente controlado;
3. revisar divergências e duplicidades;
4. validar o catálogo consolidado;
5. publicar uma nova versão imutável;
6. atualizar o manifesto após a validação.

Não será criado um formulário público de upload. A inclusão de dados é uma operação administrativa e deverá ocorrer por processo autenticado e auditável.
