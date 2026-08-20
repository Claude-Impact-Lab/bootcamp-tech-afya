# User Manager

Projeto do treinamento de programação: cadastro de médicos com validação local no CFM,
usuários sem CRM com aprovação manual e acessos separados por tipo de conta.

Hoje a tela pública cria pré-cadastros por `POST /registrations`; a lista completa e a
aprovação ficam protegidas no painel administrativo.

---

## Primeira vez? Comece aqui

Você vai fazer isso **uma vez só**. Depois disso, rodar o projeto são dois comandos.

Se você nunca usou o terminal (aquela tela preta onde se digitam comandos), leia
primeiro o [guia de terminal do Claude Code](https://code.claude.com/docs/en/terminal-guide) —
ele explica o básico no Windows e no Mac.

### 1. Instale o Git

O Git é o programa que baixa o projeto e guarda o histórico de mudanças.

➡️ **[Baixar e instalar o Git](https://git-scm.com/install/)** — escolha o seu sistema
(Windows ou macOS) na página.

Para conferir se funcionou, abra o terminal e digite:

```bash
git --version
```

Se aparecer um número de versão (ex: `git version 2.55.0`), está pronto.

### 2. Instale o uv

O `uv` cuida do Python e das bibliotecas do projeto para você. Com ele, você **não
precisa instalar o Python separadamente** — o `uv` baixa a versão certa sozinho.

➡️ **[Instalar o uv](https://docs.astral.sh/uv/getting-started/installation/)** — a
página tem o comando para Windows (PowerShell) e para macOS/Linux.

Para conferir:

```bash
uv --version
```

> **Deu "command not found" ou "não é reconhecido"?** Feche o terminal e abra de novo.
> Programas recém-instalados só aparecem em terminais abertos depois da instalação.

### 3. Conecte-se ao GitHub

Esta é a parte onde mais gente trava, então leia com calma.

**O GitHub não aceita mais a sua senha pelo terminal.** Desde 2021, digitar a senha da
conta no `git push` dá erro — mesmo estando correta. É preciso um *token*, e a forma
mais simples de conseguir um é deixar uma ferramenta fazer isso por você.

Instale o **GitHub CLI**:

➡️ **[Instalar o GitHub CLI](https://cli.github.com/)** — tem instalador para Windows
e para macOS.

Depois, no terminal:

```bash
gh auth login
```

Ele vai fazer algumas perguntas, navegando com as setas e Enter. Responda assim:

| Pergunta | Resposta |
|----------|----------|
| *Where do you use GitHub?* | `GitHub.com` |
| *What is your preferred protocol...?* | **`HTTPS`** |
| *Authenticate Git with your GitHub credentials?* | `Yes` |
| *How would you like to authenticate?* | `Login with a web browser` |

Vai aparecer um código curto (ex: `ABCD-1234`). Copie, aperte Enter, e o navegador
abre para você colar o código e confirmar.

> As perguntas variam um pouco conforme a versão do `gh`. Se alguma não aparecer, siga
> em frente — o que importa é **escolher `HTTPS`** e aceitar quando ele oferecer
> configurar o Git. É isso que faz o `git push` funcionar depois sem pedir senha, igual
> no Windows e no Mac.

Se quiser pular as perguntas, este comando faz tudo de uma vez:

```bash
gh auth login --git-protocol https --web
```

Para conferir:

```bash
gh auth status
```

Deve dizer `✓ Logged in to github.com`.

<details>
<summary>Por que não usar chave SSH? (opcional)</summary>

SSH também funciona, mas exige gerar e cadastrar uma chave em **cada** computador que
você usar. O próprio GitHub
[recomenda HTTPS](https://docs.github.com/pt/get-started/git-basics/set-up-git) para
quem está começando. Se preferir SSH, responda `SSH` na segunda pergunta — o `gh`
cria e cadastra a chave para você.

No Windows, o Git for Windows já inclui o **Git Credential Manager**, que faz esse
mesmo trabalho de guardar o token. Se você instalou o Git e o GitHub CLI, está coberto
pelos dois lados — não precisa configurar nada.
</details>

### 4. Baixe o projeto

No terminal, digite:

```bash
git clone https://github.com/Claude-Impact-Lab/bootcamp-tech-afya.git
cd bootcamp-tech-afya
```

O `git clone` cria uma pasta com o projeto. O `cd` entra nessa pasta — e é **de dentro
dela** que todos os comandos seguintes precisam ser rodados.

> **Deu `Repository not found` ou erro de permissão?** O repositório é privado. Isso
> quase sempre significa que a sua conta ainda não tem acesso — avise o tutor. Também
> pode ser que você esteja logado com outra conta: confira com `gh auth status`.

---

## Enviando seu trabalho para o GitHub

Depois de escrever código, você publica assim. Sempre em uma **branch** própria, nunca
direto na `main`:

```bash
git checkout -b missao-01           # cria sua branch
git add .                           # seleciona o que mudou
git commit -m "feat: cria GET /users"
git push -u origin missao-01        # envia para o GitHub
```

Depois, abra um Pull Request para revisão:

```bash
gh pr create --fill --web
```

O que cada comando faz:

| Comando | O que faz |
|---------|-----------|
| `git checkout -b nome` | cria uma linha de trabalho separada, para não mexer na `main` |
| `git status` | mostra o que você mudou — **rode sempre que estiver perdido** |
| `git add .` | marca as mudanças para o próximo commit |
| `git commit -m "..."` | salva um ponto no histórico, com uma descrição |
| `git push -u origin nome` | manda a sua branch para o GitHub |
| `gh pr create` | abre o Pull Request para o time revisar |

O `-u` só é necessário no **primeiro** push da branch. Depois dele, `git push` sozinho
já basta.

Mensagens de commit seguem o formato `tipo: descrição`, com tipo sendo `feat`, `fix`,
`refactor`, `test`, `docs` ou `chore`.

> **Nunca dê `push` na `main` direto.** Se o `git status` disser `On branch main`, crie
> uma branch antes com `git checkout -b nome-da-missao`. Seus commits vão junto.

---

## Rodando o projeto

Dentro da pasta do projeto:

```bash
uv sync
docker compose up -d
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Antes, copie a configuração local do banco: `cp .env.example .env`. O primeiro comando
instala tudo; o segundo sobe o PostgreSQL; o terceiro cria ou atualiza as tabelas a
partir das migrations; e o último liga o servidor. Você vai ver algo assim:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Agora abra **<http://127.0.0.1:8000>** no navegador. Deve aparecer a tabela com os
usuários que a API devolveu.

Enquanto o servidor está rodando, o terminal fica "preso" mostrando os acessos — isso
é normal. Para desligar, aperte **Ctrl + C**.

O `--reload` faz o servidor reiniciar sozinho quando você salva um arquivo. Salve,
recarregue a página, veja a mudança.

### Endereços úteis

| Endereço | O que é |
|----------|---------|
| <http://127.0.0.1:8000> | a tela |
| <http://127.0.0.1:8000/users> | a lista de usuários em JSON |
| <http://127.0.0.1:8000/health> | a resposta da API em JSON |
| <http://127.0.0.1:8000/docs> | documentação automática, onde dá para testar a API |

### Banco de dados e migrations

O PostgreSQL roda pelo Docker Compose e os dados ficam no volume `postgres_data`, então
não desaparecem quando o servidor FastAPI reinicia. O `.env` contém a configuração
local e é ignorado pelo Git; `.env.example` é o modelo seguro para colegas.

Para criar uma alteração de estrutura depois de mudar um modelo:

```bash
uv run alembic revision --autogenerate -m "descreve a alteracao"
uv run alembic upgrade head
```

Para desfazer a última migration localmente: `uv run alembic downgrade -1`.

### Cadastro público e painel administrativo

A página inicial (`/`) recebe nome, e-mail, CRM, UF e senha. Depois de salvar o cadastro,
o backend agenda a validação em segundo plano, devolve imediatamente a página de
acompanhamento e então abre o Chrome em uma sessão isolada, preenche CRM e UF no portal
público do CFM e aguarda o resultado. A tela atualiza o status automaticamente. Se
aparecer CAPTCHA, ele deve ser resolvido manualmente nessa
janela; o sistema não tenta contorná-lo. Nome, CRM e UF correspondentes com situação
`Regular` aprovam o médico automaticamente. Timeout ou fechamento da janela deixam o
cadastro como `crm_verification_pending`, disponível para nova tentativa ou análise.

O cadastro guarda o número completo do CRM e a UF separadamente. Na página pública do CFM,
o adaptador seleciona primeiro a UF e observa o próprio formulário: quando o site exibe um
prefixo fora do campo (como `52` para RJ), somente o restante é digitado no campo limitado
a sete posições. Não existe tabela fixa de prefixos no projeto. A senha é armazenada somente
como hash. Usuários sem CRM possuem cadastro e login próprios em `/non-medical/register` e
`/non-medical/login` e continuam dependendo de aprovação manual.

O administrador aprova ou rejeita cada solicitação. Na aprovação administrativa de um
médico, o sistema consulta novamente o CFM e salva automaticamente a foto e a ficha
profissional; a decisão continua sendo do administrador. Um médico aprovado passa por
`approved_incomplete` e precisa concluir a segunda etapa antes de ficar `active`. Um
usuário sem CRM aprovado fica `active` imediatamente. Ele possui um perfil próprio para
atualizar nome, e-mail, CPF e celular; se for rejeitado, pode corrigir os dados e reenviar a
solicitação. Pendentes e rejeitados conseguem
se autenticar, mas o backend bloqueia os painéis e mostra apenas o status da solicitação.
Médicos com validação pendente ou não concluída podem corrigir nome, CRM e UF nessa
página e iniciar uma nova consulta sem depender do administrador.

Após a aprovação, o médico visualiza a própria ficha validada: foto, nome oficial,
CRM/UF, situação, inscrição, especialidades, RQE e datas do CFM ficam somente para
leitura. E-mail, CPF, estado civil e celular são editáveis. O perfil pode ser salvo como
rascunho ou concluído; no escopo didático, o CPF aceita qualquer combinação com 11
dígitos, e o celular é normalizado e validado pelo backend.

Rotas dessa relação:

| Método e rota | Função |
|---------------|--------|
| `POST /registrations` | cria o médico e inicia a validação local no CFM |
| `POST /non-medical/registrations` | cria pré-cadastro sem CRM pendente |
| `POST /doctor/login` | autentica um médico e direciona conforme seu status |
| `POST /doctor/retry-cfm` | médico autenticado corrige os próprios dados e tenta novamente |
| `PUT /doctor/profile` | salva rascunho ou conclui os dados pessoais do perfil médico |
| `POST /non-medical/login` | autentica um usuário sem CRM |
| `PUT /non-medical/profile` | atualiza o perfil ou reenvia um cadastro sem CRM rejeitado |
| `POST /account/password-reset/request` | gera e envia um link temporário de recuperação |
| `POST /account/password-reset/confirm` | redefine a senha usando o link temporário |
| `POST /admin/registrations/{id}/approve` | aprova manualmente uma solicitação |
| `POST /admin/registrations/{id}/reject` | rejeita uma solicitação com motivo |
| `POST /admin/registrations/{id}/retry-cfm` | abre o Chrome para tentar o CFM novamente |
| `POST /admin/registrations/{id}/sync-cfm` | atualiza foto e ficha CFM sem alterar a aprovação |
| `POST /doctor/complete-profile` | conclui a segunda etapa do médico aprovado |
| `PUT /registrations/{user_id}` | administrador edita usuário e perfil médico |
| `POST /users/{user_id}/doctor` | adiciona perfil médico a um usuário existente |
| `GET /users/{user_id}/doctor` | consulta o perfil médico |
| `PUT /users/{user_id}/doctor` | edita CRM e UF |

O painel protegido fica em:

<http://127.0.0.1:8000/admin>

No ambiente local de demonstração, use o nome `santanna` e a senha definida em
`ADMIN_PASSWORD` no arquivo `.env`. Pelo painel, o administrador pode consultar, editar
ou excluir um cadastro. As rotas de consulta e alteração em `/users` também exigem a
sessão administrativa, inclusive quando chamadas pela página `/docs`.
O painel oferece busca por nome, e-mail ou CRM, filtros por status e paginação. Aprovações,
rejeições e o resultado da validação automática podem ser enviados por SMTP. Sem SMTP
configurado, as notificações aparecem no terminal para facilitar a demonstração local.

O processamento em segundo plano usa as tarefas internas do FastAPI, adequado ao escopo
didático e sem exigir Redis. Em uma implantação distribuída com vários servidores, essa
fila deve ser substituída por um worker persistente.

### Se algo der errado

| Mensagem | O que fazer |
|----------|-------------|
| `command not found` / `não é reconhecido` | Feche e reabra o terminal. Programas recém-instalados só aparecem em terminais novos. |
| `Address already in use` | Já existe um servidor rodando. Ache o terminal antigo e aperte Ctrl+C, ou use outra porta: `--port 8001`. |
| `No such file or directory: pyproject.toml` | Você não está na pasta do projeto. Rode `cd bootcamp-tech-afya`. |
| A tela mostra "erro ao chamar a API" | O servidor caiu. Olhe o terminal para ver o erro. |
| `Support for password authentication was removed` | Era a senha da conta. Rode `gh auth login` (passo 3). |
| `Repository not found` | Sua conta não tem acesso ao repositório — avise o tutor. Confira a conta com `gh auth status`. |
| `Updates were rejected` no push | Alguém publicou antes de você. Rode `git pull --rebase` e depois o push de novo. |
| `src refspec main does not match any` | Você não tem commits ainda. Rode `git status` para ver o que falta. |
| Travou numa tela de texto após o commit | É o editor de texto do Git. Aperte `Esc`, digite `:q` e Enter. Use `git commit -m "mensagem"` para não cair nele. |

## Testes

```bash
uv run pytest
```

Devem passar 129 testes. Se algum falhar, a mensagem diz qual e por quê. O arquivo
`tests/test_user_journeys.py` percorre as jornadas completas de médico, usuário sem CRM
e administrador.

---

## Estrutura

```
app/
  main.py              rotas e persistência da aplicação
  models.py            tabelas User, Doctor e DoctorSpecialty
  dependencies.py      injeção dos serviços nas rotas
  services/            contrato do CFM e regras de validação
  integrations/        cliente SOAP oficial do CFM
  templates/
    index.html         cadastro público
    admin.html         painel protegido
alembic/versions/      migrations do PostgreSQL
tests/
  test_main.py         testes das rotas
  test_cfm_service.py  testes do adaptador com respostas SOAP simuladas
pyproject.toml         a lista de bibliotecas do projeto
```

O contrato `CFMService` impede que as rotas dependam diretamente de SOAP ou XML. A
implementação oficial pode ser substituída nos testes sem fazer chamadas externas.

### Como a tela funciona

O `index.html` não tem nenhum nome de usuário escrito nele. Ao abrir, ele chama
`fetch("/users")` e o JavaScript cria as linhas da tabela a partir do JSON que a API
respondeu. É o primeiro contato com HTTP + JSON:

- lista vazia (`[]`) → a tela avisa "Nenhum usuário cadastrado ainda";
- servidor fora do ar ou erro HTTP → a tela mostra um aviso pedindo para recarregar,
  em vez de ficar em branco.

O formulário faz `POST /users` e, no sucesso, recarrega a lista pela API em vez de
adicionar a linha por conta própria — assim a tela mostra o que o servidor realmente
gravou (incluindo o `id` que ele gerou). Erro de validação (`422`) ou e-mail repetido
(`409`) aparecem como aviso acima da tabela.

> Os usuários vivem em memória (a lista `USERS` em `app/main.py`). Reiniciar o servidor
> apaga o que você cadastrou — o banco de verdade entra na missão 03.

---

## As 10 missões

| # | Missão | Conceito central |
|---|--------|------------------|
| 01 | `GET /users` | rotas, JSON, status codes |
| 02 | `POST /users` | request body, validação com Pydantic |
| 03 | Persistir no PostgreSQL | SQL, modelagem, migrations |
| 04 | Edição e exclusão | `PUT`, `DELETE`, idempotência |
| 05 | User + Doctor | relacionamento entre entidades |
| 06 | Validar CRM + UF | regra de negócio |
| 07 | Integrar com o CFM | adapter de dependência externa |
| 08 | Simular CFM indisponível | timeout, retry, `VALIDATION_PENDING` |
| 09 | Testes e mocks | não depender do serviço externo |
| 10 | Publicar e apresentar | deploy, README, code review |

## Usando IA para aprender

Você pode e deve usar Claude, Codex e similares. A regra do treinamento é:
**pesquisar e investigar é permitido; copiar a solução pronta sem entender, não.**

O que funciona bem:

- Peça **explicação**, não só código: "o que esse erro significa?", "por que isso
  funciona?"
- Cole a mensagem de erro inteira. Ela costuma dizer exatamente o que está errado.
- Peça para a IA revisar o que **você** escreveu, em vez de escrever por você.
- Depois de receber código, pergunte a si mesmo: eu saberia explicar isso no code
  review? Se não, pergunte mais.

Se for usar o Claude Code no terminal: [instalação](https://code.claude.com/docs/en/setup)
e [primeiros passos](https://code.claude.com/docs/en/quickstart).

---

## Integração opcional com o CFM (histórico da missão 07)

O projeto mantém o adapter do **Webservice oficial** de Listagem de Médicos, sem scraping. O adapter
`CFMSoapService` envia `Consultar(CRM, UF, chave)` por SOAP 1.1/TLS 1.2 e transforma o
XML em um objeto interno. O CFM devolve nome, CRM, UF, tipo e situação da inscrição,
data de atualização e zero ou várias especialidades. CPF, endereço, telefone e e-mail
não vêm nessa consulta.

Para usar a integração real, uma pessoa jurídica precisa contratar o serviço junto ao
CFM e colocar a chave somente no `.env`:

```env
CFM_ACCESS_KEY=sua-chave-de-8-caracteres
CFM_WS_URL=https://ws.cfm.org.br:8080/WebServiceConsultaMedicos/ServicoConsultaMedicos
CFM_TIMEOUT_SECONDS=10
```

Essa integração não é chamada pelo fluxo atual. Sem uma chave válida, o servidor e o
pré-cadastro continuam funcionando normalmente; a validação é feita pelo administrador.

Referências: [Webservice do CFM](https://sistemas.cfm.org.br/listamedicos/informacoes),
[manual oficial](https://sistemas.cfm.org.br/listamedicos/arquivos/manualwebservices.pdf)
e [Resolução CFM nº 2.309/2022](https://sistemas.cfm.org.br/normas/arquivos/resolucoes/BR/2022/2309_2022.pdf).
