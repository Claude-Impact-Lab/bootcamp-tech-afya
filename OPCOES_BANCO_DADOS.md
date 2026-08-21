# ⚡ GUIA RÁPIDO: 3 MANEIRAS DE RODAR O PROJETO

## 🚀 Escolha UMA das 3 opções abaixo

---

## ✅ OPÇÃO 1: SQLite Local (AGORA - RECOMENDADO) ⭐

### Pré-requisitos
- ✅ Já configurado!

### Execute
```powershell
.\start.ps1
```

### Onde o banco fica
```
Arquivo: usermanager.db
Pasta: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\
Tipo: Disco Rígido (HD)
Tamanho: ~100KB
```

### Visualizar
```powershell
# No Windows Explorer
explorer C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\
# Você verá o arquivo usermanager.db
```

### ✨ Vantagens
- ✅ Funciona AGORA
- ✅ Sem Docker
- ✅ Sem dependências
- ✅ Rápido
- ✅ Dados persistem

### ⚠️ Limitações
- ❌ Um usuário por vez (acesso simultâneo limitado)
- ❌ Não ideal para múltiplas máquinas

---

## 🐳 OPÇÃO 2: PostgreSQL em Docker (FUTURO)

### Pré-requisitos
1. Instale [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Abra Docker Desktop (pode levar 30s-1min)

### Configure `.env`
```env
DATABASE_URL=postgresql://user:password@localhost:5432/usermanager
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=usermanager
```

### Execute
```powershell
.\start.ps1
```

### Onde o banco fica
```
Volume Docker: /var/lib/postgresql/data (dentro do container)
Sincronizado com: C:\ProgramData\Docker\volumes\... (seu HD)
Tipo: Disco Rígido (HD)
Tamanho: ~500MB
```

### Verificar
```powershell
# Listar containers
docker ps

# Ver dados
docker-compose exec postgres psql -U user -d usermanager -c "SELECT * FROM users;"

# Parar
docker-compose down
```

### ✨ Vantagens
- ✅ Múltiplos usuários simultâneos
- ✅ Profissional
- ✅ Pronto para produção
- ✅ Seu colega roda no Mac/Linux e funciona igual

### ⚠️ Limitações
- ❌ Precisa Docker instalado
- ❌ Mais lento que SQLite
- ❌ Maior consumo de espaço

---

## 🗄️ OPÇÃO 3: PostgreSQL Local Instalado

### Pré-requisitos
1. Instale [PostgreSQL](https://www.postgresql.org/download/)
2. Crie banco de dados `usermanager`

### Configure `.env`
```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/usermanager
```

### Execute
```powershell
.\start.ps1
```

### Onde o banco fica
```
Diretório PostgreSQL: C:\Program Files\PostgreSQL\xx\data\
Tipo: Disco Rígido (HD)
Tamanho: ~200MB
```

### Verificar
```powershell
# Conectar ao banco
psql -U seu_usuario -d usermanager

# Ver usuários
SELECT * FROM users;

# Sair
\q
```

### ✨ Vantagens
- ✅ Nenhuma virtualização
- ✅ Integrado ao SO
- ✅ Pode usar em outras aplicações

### ⚠️ Limitações
- ❌ Apenas Windows (se não usar Linux/Mac)
- ❌ Mais complexo desinstalar
- ❌ Conflito se múltiplos projetos usarem

---

## 📊 Comparação: Onde Fica o Banco?

| Opção | Arquivo/Pasta | Local Físico | Armazenamento | Tamanho | Compartilhado |
|-------|---|---|---|---|---|
| **SQLite** | `usermanager.db` | Pasta projeto | HD | ~100KB | ❌ |
| **Docker** | Volume Docker | HD (virual) | HD | ~500MB | ✅ (entre projetos) |
| **Local** | Diretório PG | `C:\Program Files\...` | HD | ~200MB | ✅ (entre programas) |

---

## 🎯 QUAL ESCOLHER AGORA?

```
Você está em desenvolvimento? → OPÇÃO 1 (SQLite) ⭐
  - Simples
  - Nenhuma dependência
  - Funciona agora
  
Você quer praticar Docker? → OPÇÃO 2 (Docker)
  - Mais profissional
  - Aprende Docker
  - Seus colegas rodam no Mac também
  
Você já tem PostgreSQL? → OPÇÃO 3 (Local)
  - Reutiliza o que já tem
  - Um pouco mais complexo
```

### 👉 RECOMENDAÇÃO: Comece com OPÇÃO 1 (SQLite) agora!

---

## 🔄 Migrar Depois

Ótimo do SQLite → PostgreSQL:
- Dados não se perdem
- Código não muda muito
- Próxima missão (04) mostra como fazer

---

## ✅ CHECKLIST: Tudo Pronto?

- ✅ `.env` configurado (SQLite por padrão)
- ✅ `pyproject.toml` com dependências
- ✅ `database.py` atualizado
- ✅ `main.py` com try-except robusto
- ✅ `start.ps1` detecta automaticamente
- ✅ 6/6 testes passando
- ✅ Documentação completa

---

## 🚀 AGORA: Teste!

### Passo 1: Rodar servidor
```powershell
.\start.ps1
```

Saída esperada:
```
Docker não instalado. Usando SQLite local.
Banco será armazenado em: usermanager.db
...
Iniciando o servidor...
Acesse http://localhost:8000 no seu navegador.
```

### Passo 2: Abrir navegador
```
http://localhost:8000
```

### Passo 3: Criar usuários
- Clique em "Cadastrar usuário"
- Preencha nome e email
- Clique "Cadastrar"

### Passo 4: Verificar banco
```powershell
# Em outro terminal
cd C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\

# Ver arquivo do banco
dir usermanager.db

# Ver tamanho (em bytes)
(Get-Item usermanager.db).Length
```

### Passo 5: Reiniciar servidor
```
1. Ctrl+C no terminal (para o servidor)
2. .\start.ps1 (reinicia)
3. Abra http://localhost:8000 novamente
4. Veja que os usuários continuam lá! ✨
```

---

## 📍 RESPOSTA FINAL: ONDE ESTÁ O BANCO?

### SQLite (AGORA)
```
📁 Arquivo: usermanager.db
📍 Pasta: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\usermanager.db
💾 Armazenado: DISCO RÍGIDO (HD/SSD)
🔄 Persiste: SIM, para sempre
📊 Tamanho: ~100KB para 1000 usuários
🚀 Velocidade: Muito rápido (local)
🔐 Segurança: Seguro (não precisa rede)
```

### PostgreSQL Docker (FUTURO)
```
📁 Volume: /var/lib/postgresql/data
📍 Mapeado: C:\ProgramData\Docker\volumes\...
💾 Armazenado: DISCO RÍGIDO (HD/SSD)
🔄 Persiste: SIM, para sempre
📊 Tamanho: ~500MB (com overhead)
🚀 Velocidade: Rápido (localhost)
🔐 Segurança: Container isolado
```

### PostgreSQL Local (FUTURO)
```
📁 Diretório: C:\Program Files\PostgreSQL\xx\data\
📍 Pasta: HD local
💾 Armazenado: DISCO RÍGIDO (HD/SSD)
🔄 Persiste: SIM, para sempre
📊 Tamanho: ~200MB (com overhead)
🚀 Velocidade: Rápido (local)
🔐 Segurança: Integrado ao SO
```

---

## 💡 Entender: RAM vs HD

```
RAM (Memória):
  - Rápida ⚡
  - Desaparece ao desligar PC 💥
  - Durante db.add() os dados ficam aqui
  
HD/SSD (Disco):
  - Mais lenta (mas ainda rápida)
  - Persiste ao desligar PC ✅
  - Após db.commit() os dados ficam aqui

Seu projeto:
  1. Usuário faz POST /users
  2. Dados carregam em RAM (rápido)
  3. db.commit() escreve em HD (persistente)
  4. Ao reiniciar → dados recuperados do HD
```

---

## 🎉 Resumo Final

**Você agora tem 3 formas de rodar o projeto:**

1. **SQLite** (AGORA) - Funciona, sem Docker
   - Banco em: `C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\usermanager.db`
   - Tipo: Arquivo local no HD
   
2. **PostgreSQL Docker** (FUTURO) - Quando instalar Docker
   - Banco em: `C:\ProgramData\Docker\volumes\...`
   - Tipo: Volume Docker sincronizado com HD
   
3. **PostgreSQL Local** (FUTURO) - Se instalar PostgreSQL
   - Banco em: `C:\Program Files\PostgreSQL\...`
   - Tipo: Diretório PostgreSQL no HD

**Todos armazenam dados no DISCO RÍGIDO (HD/SSD), não na RAM!**

Pronto! Agora execute:
```powershell
.\start.ps1
```

🚀 Bom desenvolvimento!
