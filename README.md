# User Manager

Projeto do treinamento de programação: um cadastro de usuários que vai evoluir até
validar médicos no Webservice oficial do CFM.

Hoje o projeto está no ponto de partida: uma tela que mostra **Hello World**,
buscando a mensagem da própria API. Cada missão adiciona uma camada a partir daqui.

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
uv run uvicorn app.main:app --reload
```

O primeiro comando instala tudo (demora um pouco na primeira vez). O segundo liga o
servidor. Você vai ver algo assim:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Agora abra **<http://127.0.0.1:8000>** no navegador. Deve aparecer **Hello World**.

Enquanto o servidor está rodando, o terminal fica "preso" mostrando os acessos — isso
é normal. Para desligar, aperte **Ctrl + C**.

O `--reload` faz o servidor reiniciar sozinho quando você salva um arquivo. Salve,
recarregue a página, veja a mudança.

### Endereços úteis

| Endereço | O que é |
|----------|---------|
| <http://127.0.0.1:8000> | a tela |
| <http://127.0.0.1:8000/health> | a resposta da API em JSON |
| <http://127.0.0.1:8000/docs> | documentação automática, onde dá para testar a API |

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

Devem passar 2 testes. Se algum falhar, a mensagem diz qual e por quê.

---

## Estrutura

```
app/
  main.py              as rotas da aplicacao
  templates/
    index.html         a tela
tests/
  test_main.py         os testes
pyproject.toml         a lista de bibliotecas do projeto
```

Ainda **não** existem pastas para `services`, `repositories` ou integrações. Elas
entram nas missões em que forem necessárias, para que o motivo de cada camada fique
claro antes de ela existir.

### Como a tela funciona

O `index.html` não tem a palavra "Hello World" escrita nele. Ele chama a API com
`fetch("/health")` e escreve na página o que a API respondeu. É o primeiro contato
com HTTP + JSON: se a API cair, a tela mostra o erro em vez do texto.

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

## Sobre a integração com o CFM (missão 07 em diante)

- Usar o **Webservice oficial** de listagem de médicos. Não fazer scraping.
- O CFM devolve dados públicos: nome, CRM, UF, tipo e situação da inscrição e
  especialidade registrada. CPF, endereço, telefone e e-mail **não** vêm nesse
  serviço.
- Guardar `cfm_validated_at` para saber quando a validação foi feita.
- A dependência externa fica isolada em um client com contrato próprio
  (`find_doctor(crm, uf)`), para o domínio não se acoplar ao formato do CFM.

Referências: [Webservice do CFM](https://sistemas.cfm.org.br/listamedicos/informacoes)
e a Resolução CFM nº 2.309/2022.

### Implementação desta versão de teste

Nesta versão de teste, a aplicação automatiza o formulário público do CFM com
Playwright. O navegador seleciona a UF, preenche o CRM, envia o formulário pelo
fluxo normal da página e captura a resposta AJAX produzida pelo próprio portal.
A dependência continua isolada em `app/cfm_client.py`, cujo contrato público é
`find_doctor(crm, uf)`.

Depois de instalar as dependências, instale uma vez o Chromium usado pela
automação:

```bash
uv run playwright install chromium
```

Por padrão, `CFM_BROWSER_MODE=background`: a aplicação usa um Chromium normal,
mas mantém a janela fora da área visível. A UF e o CRM são preenchidos e
enviados automaticamente. A janela só é movida para a frente quando a página
apresenta o desafio visual do reCAPTCHA. A tentativa inteira é limitada a menos
de 60 segundos. Também é possível configurar:

- `CFM_BROWSER_MODE=headless`: nunca abre uma janela;
- `CFM_BROWSER_MODE=headless_then_headed`: tenta oculto antes do modo visível.
- `CFM_BROWSER_MODE=headed`: mostra a janela desde o início.

- `VALIDATED`: a resposta contém exatamente a UF e o CRM consultados;
- `NOT_FOUND`: a resposta foi concluída, mas não contém a combinação consultada;
- `VALIDATION_PENDING`: o portal não respondeu, pediu reCAPTCHA ou mudou a página.
  Nesse caso o cadastro é salvo como pendente e a tela oferece a consulta manual
  já preenchida com UF e CRM.

No RJ, o prefixo fixo `52`, exibido separadamente pelo portal, é retirado antes
do preenchimento e da comparação. O código não resolve nem contorna reCAPTCHA.
Como o portal é externo e pode mudar, os testes automatizados simulam a resposta
do CFM e não dependem de internet.

O CRM é armazenado em formato canônico e o par `UF + CRM` é protegido por um
índice único composto no PostgreSQL. O mesmo número pode existir em UFs
diferentes. Uma nova tentativa com o mesmo par somente é tratada como login se
nome e e-mail também forem iguais; qualquer divergência é recusada sem criar
outro registro.

No painel Admin, o botão **Validar todos** percorre os médicos pendentes um por
um. A linha em consulta troca as ações por um indicador de carregamento. Uma
confirmação automática move o cadastro para a lista de médicos; resultados não
confirmados permanecem pendentes para decisão manual. Um segundo clique no
botão envia um sinal de cancelamento ao backend e interrompe a fila atual.
