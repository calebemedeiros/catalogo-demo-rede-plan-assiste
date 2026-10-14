# Segurança do catálogo

O catálogo não recebe dados de beneficiários nem utiliza credenciais. Cada integração deve apontar para uma API pública HTTPS e retornar JSON por uma chamada documentada.

## Controles obrigatórios

- lista positiva de hosts, campos e URLs;
- `GET` sem autenticação e sem redirecionamento automático;
- timeout e validação de `Content-Type`;
- ausência de varredura por letras, identificadores ou combinações artificiais;
- descarte de respostas brutas em diretório temporário;
- checksums SHA-256 no manifesto;
- publicação somente por artefato, com permissões mínimas;
- nenhuma inclusão de CPF, matrícula, carteirinha, sexo, observações ou imagens.

Uma API pública pode recusar o executor do GitHub. Nessa condição, a fonte é marcada como indisponível e nenhuma técnica de contorno é utilizada.
