# Projeto Transferências

API de carteira digital desenvolvida com Python, FastAPI, PostgreSQL e Docker Compose.

## Requisitos
- Docker Desktop (ou Docker Engine) com Compose
- Git (para publicar no GitHub)

## Executar
Na pasta do projeto:

```bash
docker compose up --build -d
```

A API ficará em http://localhost:8080 e a documentação interativa em http://localhost:8080/docs.

Verifique:
```bash
docker compose ps
docker compose logs -f api
```

## Atenção à persistência
- `docker compose stop` e `docker compose start`: mantêm os dados.
- `docker compose down` e depois `docker compose up -d`: mantêm o volume de dados.
- `docker compose down -v`: APAGA o volume do PostgreSQL e, portanto, apaga os dados. O enunciado pede testar também `down -v`; esse comando reinicia a aplicação limpa, mas não pode preservar dados que o próprio Docker foi instruído a apagar.

## Rotas

| Método | Rota | Autenticação |
|---|---|---|
| POST | `/auth/registrar` | Não |
| POST | `/auth/login` | Não |
| GET | `/conta` | Bearer |
| POST | `/transferencias` | Bearer |
| GET | `/auditoria` | Não |

### Fluxo de teste pelo Swagger
1. Abra `/docs`.
2. `POST /auth/registrar`: `{"username":"joao","password":"senha123"}`.
3. Registre Maria: `{"username":"maria","password":"senha123"}`.
4. Faça login do João em `/auth/login` e copie o token.
5. Clique em **Authorize** e informe `Bearer SEU_TOKEN` (se o Swagger pedir apenas o token, informe o token sem o prefixo).
6. Consulte `/conta`.
7. Faça `POST /transferencias`: `{"destino":"maria","valor":150}`.
8. Consulte `/conta` novamente: saldo esperado 850.
9. Faça novamente a mesma transferência em menos de 60 segundos: deve retornar `409 {"error":"TRANSFERENCIA_DUPLICADA"}`.
10. Consulte `/auditoria`: dois usuários, soma dos saldos 2000 e uma transferência efetivada.

Para testar Maria, faça login com Maria e substitua o token no botão Authorize.

## Estratégia de concorrência e integridade
A transferência usa uma única transação PostgreSQL. As linhas das contas de origem e destino são bloqueadas com `SELECT ... FOR UPDATE`, sempre em ordem crescente de ID para reduzir deadlocks em transferências cruzadas. Assim, operações concorrentes que envolvem as mesmas contas são serializadas e os créditos simultâneos não sobrescrevem o saldo uns dos outros. Débito, crédito e gravação do histórico são confirmados juntos; se houver erro antes do commit, o banco desfaz tudo.

A verificação de duplicidade considera origem, destino, valor e janela de 60 segundos, e acontece antes da verificação de saldo, como especificado.

## Observação importante sobre o enunciado
O comando `docker compose down -v` remove volumes nomeados. Portanto, é tecnicamente impossível preservar os dados depois desse comando. Para demonstrar persistência, use `docker compose down` (sem `-v`) ou `stop/start`. Use `down -v` somente para testar uma instalação limpa.

## Publicar no GitHub
Crie um repositório vazio no GitHub. Dentro da pasta do projeto:

```bash
git init
git add .
git commit -m "Projeto inicial de API de transferencias"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git push -u origin main
```

Não envie o arquivo `.env` nem senhas reais. O `.gitignore` já ignora `.env`.

## Limitações / próximos aprimoramentos
Esta entrega é uma base funcional para o desafio. Para produção, configure segredo JWT seguro, migrações Alembic, limites de requisição, logs estruturados, monitoramento e testes automatizados de carga/concorrência. O projeto não oferece endpoint para alterar senha ou excluir usuários.
