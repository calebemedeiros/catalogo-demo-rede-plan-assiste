# Catálogo demonstrativo da rede Plan-Assiste

API estática utilizada pelo painel nacional da rede Plan-Assiste para demonstrar o consumo de uma fonte externa e a consolidação de diferentes formas de acesso.

## Importante

Todos os registros são sintéticos. Este repositório não contém nomes, registros profissionais, telefones ou endereços reais e não representa a rede oficial do Plan-Assiste, AMHPDF, CNU, FESP, Unimeds ou Rede D'Or. A presença de um registro não representa cobertura, autorização ou disponibilidade.

## Composição da amostra

- 300 médicos da fonte **AMHPDF — amostra demonstrativa**;
- 60 registros de **credenciamento direto demonstrativo**;
- 60 registros sintéticos para cada fonte CNU, FESP, Unimeds regionais e Rede D'Or;
- 600 registros no total;
- 500 profissionais e 100 estabelecimentos;
- 48 especialidades e categorias assistenciais;
- 20 UFs representadas por localidades inteiramente simuladas.

## Endpoints estáticos

Após a publicação no GitHub Pages:

```text
/api/v1/manifest.json
/api/v1/prestadores.json
/api/v1/fontes/amhpdf-demo.json
/api/v1/fontes/plan-assiste-direto-demo.json
/api/v1/fontes/cnu-demo.json
/api/v1/fontes/fesp-demo.json
/api/v1/fontes/unimeds-demo.json
/api/v1/fontes/rede-dor-demo.json
```

O painel consulta primeiro o manifesto, verifica a versão, o ambiente, a autorização demonstrativa, a quantidade de registros e o SHA-256. Somente depois carrega o catálogo.

## Gerar e validar

```powershell
npm run build
```

O gerador é determinístico. Executar novamente o comando produz a mesma base e o mesmo checksum enquanto os parâmetros permanecerem inalterados.

## Adicionar uma fonte

Consulte [docs/COMO_ADICIONAR_UMA_FONTE.md](docs/COMO_ADICIONAR_UMA_FONTE.md). A inclusão de uma fonte real dependerá de autorização, minimização dos campos, validação institucional e armazenamento apropriado.

## Segurança

- nenhuma credencial é utilizada no navegador;
- os dados reais permanecem bloqueados nesta fase;
- a publicação exige validação automatizada;
- campos administrativos conhecidos são rejeitados;
- todos os registros precisam ser identificados como sintéticos;
- o catálogo é protegido por checksum SHA-256.
