# 💾 ONDE O BANCO DE DADOS É ARMAZENADO?

## ⚡ RESPOSTA RÁPIDA

### Agora (SQLite - SEM Docker)
```
📁 Arquivo: usermanager.db
📍 Local: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\usermanager.db
💾 Tipo: DISCO RÍGIDO (HD)
🔄 Persiste: Sim, para sempre (até deletar arquivo)
⚡ Velocidade: Muito rápido (~1000x mais rápido que rede)
```

---

## 📊 Visualizar o Banco

### 1. No Windows Explorer
```
1. Abra: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\
2. Você verá arquivo: usermanager.db (50-100KB)
3. É um arquivo SQLite binário
```

### 2. No PowerShell (verificar tamanho)
```powershell
# Ver arquivo do banco
Get-Item usermanager.db

# Ver tamanho
(Get-Item usermanager.db).Length  # Em bytes
```

### 3. Visualizar conteúdo (via Python)
```python
import sqlite3

# Conectar ao banco
conn = sqlite3.connect('usermanager.db')
cursor = conn.cursor()

# Ver todos os usuários
cursor.execute("SELECT * FROM users")
usuarios = cursor.fetchall()

print(usuarios)
# [(1, 'João Silva', 'joao@example.com'), ...]

conn.close()
```

---

## 🔍 Entender a Arquitetura de Armazenamento

### SQLite (AGORA)
```
┌─────────────────────────────────────┐
│ Sua Aplicação (Python/FastAPI)      │
└────────────────┬────────────────────┘
                 │ (lê/escreve)
                 ▼
        ┌─────────────────┐
        │ SQLite (memória)│
        └────────┬────────┘
                 │ (sincroniza)
                 ▼
    ┌────────────────────────┐
    │ Arquivo: usermanager.db│
    │ Localização: C:\...\   │
    │ Tipo: Disco Rígido     │
    │ Tamanho: ~100KB        │
    └────────────────────────┘

Fluxo:
1. Você cria usuário na aplicação
2. FastAPI → SQLAlchemy → SQLite (em memória)
3. SQLite sincroniza com arquivo .db no disco
4. Arquivo persiste mesmo se desligar computador
```

### PostgreSQL em Docker (FUTURO)
```
┌─────────────────────────────────────┐
│ Sua Aplicação (Python/FastAPI)      │
└────────────────┬────────────────────┘
                 │ (rede localhost:5432)
                 ▼
        ┌─────────────────────┐
        │ PostgreSQL Container│
        │ (rodando em Docker) │
        └────────────┬────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Volume Docker          │
        │ (/var/lib/postgresql)  │
        └────────────┬───────────┘
                     │ (mapeia para)
                     ▼
        ┌────────────────────────────┐
        │ Disco Rígido do seu PC     │
        │ C:\ProgramData\Docker\...  │
        │ Tamanho: ~500MB            │
        └────────────────────────────┘

Fluxo:
1. Você cria usuário na aplicação
2. FastAPI → SQLAlchemy → psycopg2 (driver)
3. Conexão TCP/IP para localhost:5432
4. PostgreSQL recebe comando SQL
5. PostgreSQL escreve em volume Docker
6. Volume persiste em disco
```

---

## 📈 Tamanho do Banco

### SQLite
```
Usuário vazio:     ~5 KB
1 usuário:        ~10 KB
100 usuários:     ~50 KB
1.000 usuários:   ~100 KB
10.000 usuários:  ~500 KB
100.000 usuários: ~5 MB
```

### PostgreSQL
```
Usuário vazio:     ~50 MB (muito overhead)
1 usuário:        ~50 MB
100 usuários:     ~60 MB
1.000 usuários:   ~70 MB
10.000 usuários:  ~100 MB
100.000 usuários: ~200 MB
```

**SQLite é mais eficiente de espaço!**

---

## 🔄 Ciclo de Vida do Dados

### 1. Criar usuário
```
POST /users
  ↓
FastAPI recebe
  ↓
SQLAlchemy cria objeto User
  ↓
db.add(usuario)  ← em memória (RAM)
  ↓
db.commit()  ← AQUI escreve no arquivo usermanager.db
  ↓
Usuário salvo permanentemente no disco! ✅
```

### 2. Reiniciar servidor
```
.\start.ps1
  ↓
SQLite lê arquivo usermanager.db do disco
  ↓
Carrega dados em memória
  ↓
GET /users retorna usuários
  ↓
Dados intactos! ✨
```

### 3. Ligar e desligar computador
```
Desligar:
  Dados em memória são perdidos
  Dados no disco (usermanager.db) são salvos
  ↓
Ligar novamente:
  usermanager.db lido do disco
  Dados recuperados
  ↓
Tudo intacto! ✅
```

---

## 🎯 Localização Exata

### Arquivo SQLite
```
Caminho completo: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\usermanager.db

Partes:
C:\                               ← Raiz HD
  Users\                          ← Pasta Usuários Windows
    junio\                        ← Seu usuário Windows
      Desktop\                    ← Desktop
        PROJETO11\                ← Pasta do projeto
          bootcamp-tech-afya\     ← Seu projeto
            usermanager.db        ← BANCO DE DADOS! 💾
```

### Como encontrar via PowerShell
```powershell
# Navegar até lá
cd C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\

# Listar arquivos
ls

# Você verá:
#   usermanager.db  ← Este arquivo!

# Abrir pasta
explorer .

# Você verá o arquivo no Windows Explorer
```

---

## 💾 Dados Estão em RAM ou HD?

### A Resposta Técnica

**Ambos!** Entenda assim:

```
Dados em MEMÓRIA (RAM):
  ├─ Quando você cria um usuário
  ├─ FastAPI processa em RAM
  ├─ Rápido! (nanosegundos)
  └─ SE DESLIGAR = PERDIDO (antes do commit)

Dados em DISCO (HD):
  ├─ Quando você faz db.commit()
  ├─ SQLite escreve em usermanager.db
  ├─ Mais lento (milissegundos)
  └─ SE DESLIGAR = SEGURO (já está no HD)
```

### No Seu Projeto

```python
@app.post("/users")
def criar_usuario(dados, db: Session = Depends(get_db)):
    usuario = User(nome=dados.nome, email=dados.email)
    db.add(usuario)          # ← Apenas em RAM
    db.commit()              # ← AQUI escreve no HD (usermanager.db)
    db.refresh(usuario)
    return usuario
    
# Resumo: Ao retornar a resposta, dados já estão salvos no HD!
```

---

## 🔐 Segurança dos Dados

### SQLite Local
```
Vantagens:
  ✅ Arquivo único (fácil backup)
  ✅ Nenhuma conexão rede (mais seguro)
  ✅ Não precisa credenciais
  ✅ Criptografia nativa do SO (NTFS)

Desvantagens:
  ❌ Um arquivo = um ponto de falha
  ❌ Acesso simultâneo limitado
  ❌ Máquina desliga = risco (embora raro)
```

### PostgreSQL
```
Vantagens:
  ✅ Múltiplos usuários simultâneos
  ✅ Backup automático
  ✅ Replicação e redundância
  ✅ Muito mais robusto

Desvantagens:
  ❌ Mais complexo
  ❌ Precisa de rede
  ❌ Mais espaço em disco
```

---

## 📋 Resumo: Onde Exatamente?

| Aspecto | Resposta |
|---------|----------|
| **Arquivo** | `usermanager.db` |
| **Pasta** | `C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\` |
| **Tipo Armazenamento** | Disco Rígido (HD/SSD) |
| **Tipo Memória** | RAM durante processamento, HD ao fazer commit |
| **Tamanho** | ~100KB para 1000 usuários |
| **Formato** | SQLite (binário) |
| **Persiste?** | Sim, para sempre |
| **Compartilhado?** | Não (só este computador) |
| **Visível Windows?** | Sim, arquivo comum |
| **Pode deletar?** | Sim, mas perde todos os dados |
| **Pode copiar?** | Sim, fácil backup |

---

## ✨ Exemplo Prático

### Passo 1: Abrir arquivo no Windows
```
1. Abra: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\
2. Você verá arquivo: usermanager.db
3. Clique com botão direito → Propriedades
4. Veja tamanho, data de modificação, etc
```

### Passo 2: Verificar conteúdo em Python
```python
import sqlite3

conn = sqlite3.connect('usermanager.db')
cursor = conn.cursor()

# Listar tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cursor.fetchall())  # [('users',), ...]

# Ver estrutura da tabela
cursor.execute("PRAGMA table_info(users)")
print(cursor.fetchall())
# [(0, 'id', 'INTEGER', 1, None, 1),
#  (1, 'nome', 'VARCHAR(255)', 1, None, 0),
#  (2, 'email', 'VARCHAR(255)', 1, None, 0)]

# Ver dados
cursor.execute("SELECT * FROM users")
print(cursor.fetchall())  # [(1, 'João', 'joao@example.com'), ...]

conn.close()
```

### Passo 3: Backup
```powershell
# Copiar arquivo para ter backup
Copy-Item usermanager.db usermanager_backup_2024_08_12.db

# Arquivo backup criado:
# usermanager_backup_2024_08_12.db
```

---

## 🔮 Quando Mudar para PostgreSQL

```
Seu projeto começa:
  SQLite (desenvolvimento rápido)
         ↓ (cresce)
  PostgreSQL (produção)

Quando mudar?
  - Mais de 100K usuários
  - Múltiplos computadores acessando
  - Precisa de alta disponibilidade
  - Aplicação em produção

Como mudar?
  Fácil! Basta atualizar DATABASE_URL no .env
  Próxima missão (04) vai mostrar como migrar dados
```

---

## 🎯 Conclusão

**ONDE ESTÁ SEU BANCO?**

```
📁 Arquivo: usermanager.db
📍 Pasta: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\
💾 Armazenado: DISCO RÍGIDO (não RAM)
🔄 Persiste: SIM, para sempre
⚡ Velocidade: Muito rápido
🔐 Segurança: Seguro (arquivo local)

👉 Você pode abrir a pasta e VER o arquivo agora mesmo!
```

Pronto! Banco criado e funcional sem Docker! 🎉
