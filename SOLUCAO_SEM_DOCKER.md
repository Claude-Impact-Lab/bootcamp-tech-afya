# 🎯 Solução: Executando SEM Docker

## ✅ O Problema Resolvido

Você **não tinha Docker instalado**, então a aplicação não conseguia subir PostgreSQL.

## ✨ A Solução

Agora o projeto funciona de **3 formas**:

---

## 📊 Opção 1: SQLite Local (RECOMENDADO AGORA) ⭐

**O que é:** Banco de dados armazenado em arquivo local  
**Onde fica:** `C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\usermanager.db`  
**Vantagens:**
- ✅ Não precisa Docker
- ✅ Não precisa instalar PostgreSQL
- ✅ Funciona agora mesmo!
- ✅ Rápido
- ✅ Dados persistem entre reinicializações

**Como usar:**
```powershell
.\start.ps1
```

Pronto! Banco criado em `usermanager.db` (arquivo local)

---

## 📊 Opção 2: PostgreSQL em Docker (FUTURO)

**Como instalar:**
1. [Baixe Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Instale e abra o Docker Desktop
3. Execute `.\start.ps1`

O script vai detectar Docker automaticamente e usar PostgreSQL em container.

---

## 📊 Opção 3: PostgreSQL Local Instalado

Se você instalar PostgreSQL diretamente na máquina:
1. Instale [PostgreSQL](https://www.postgresql.org/download/)
2. Crie banco de dados `usermanager`
3. Atualize `.env`:
```env
DATABASE_URL=postgresql://seu_usuario:senha@localhost:5432/usermanager
```
4. Execute `.\start.ps1`

---

## 🎯 **AGORA: Execute isto**

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

---

## 📍 ONDE OS DADOS SÃO ARMAZENADOS?

### Com SQLite (AGORA) 💾
```
Arquivo: usermanager.db
Localização: C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\usermanager.db
Armazenado em: DISCO RÍGIDO (HD)

O que acontece:
- Arquivo criado na pasta do projeto
- Todos os usuários salvos neste arquivo
- Ao reiniciar o servidor → dados continuam lá
- Ao deletar arquivo → banco reseta

Tamanho típico: ~50KB para 1000 usuários
```

**Localização precisa:**
```powershell
# Abrir a pasta do projeto
explorer C:\Users\junio\Desktop\PROJETO11\bootcamp-tech-afya\
# Você verá: usermanager.db ← banco de dados!
```

---

### Com PostgreSQL em Docker (FUTURO) 🐘
```
Armazenado em: VOLUME DO DOCKER
Localização no Docker: /var/lib/postgresql/data
Localização no seu HD: C:\ProgramData\Docker\volumes\

O que acontece:
1. Docker cria um volume
2. Dados armazenados neste volume
3. Volume persiste mesmo com container parado
4. Ao fazer docker-compose down -v → apaga tudo

Tamanho típico: ~100MB para 100K usuários (mais overhead que SQLite)
```

---

### Com PostgreSQL Instalado Localmente
```
Armazenado em: HD (diretório PostgreSQL)
Localização: C:\Program Files\PostgreSQL\xx\data\

O que acontece:
1. PostgreSQL cria diretórios na instalação
2. Dados persistem enquanto PostgreSQL roda
3. Ao desinstalar PostgreSQL → dados perdidos
```

---

## 🎯 Comparação: Onde Fica o Banco?

| Tipo | Localização | Tipo Armazenamento |
|------|-------------|-------------------|
| **SQLite** (AGORA) | `usermanager.db` no projeto | HD (arquivo) |
| **PostgreSQL Docker** | `/var/lib/postgresql/data` | Volume Docker (HD) |
| **PostgreSQL Local** | `C:\Program Files\PostgreSQL\...\data` | HD direto |
| **SQLite em memória** (testes) | RAM | Desaparece ao sair teste |

---

## ✨ O Arquivo usermanager.db

### Visualizar dados (sem abrir arquivo)
```powershell
# Abrir REPL do Python
uv run python

# Dentro do Python:
>>> import sqlite3
>>> conn = sqlite3.connect('usermanager.db')
>>> cursor = conn.cursor()
>>> cursor.execute("SELECT * FROM users")
>>> cursor.fetchall()
[(1, 'Joao Silva', 'joao@example.com'), ...]
>>> conn.close()
```

### Backup do banco
```powershell
# Copiar arquivo para salvar
Copy-Item usermanager.db usermanager_backup.db
```

### Resetar banco
```powershell
# Deletar arquivo e banco será recriado vazio
Remove-Item usermanager.db
# Próxima vez que rodar start.ps1 → banco novo e vazio
```

---

## 🔀 Mudar de SQLite para PostgreSQL depois

Quando quiser usar PostgreSQL de verdade:

1. **Instale Docker Desktop**
   - https://www.docker.com/products/docker-desktop

2. **Atualize `.env`:**
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/usermanager
   POSTGRES_USER=user
   POSTGRES_PASSWORD=password
   POSTGRES_DB=usermanager
   ```

3. **Execute:**
   ```powershell
   .\start.ps1
   ```

É isso! Script detecta PostgreSQL e usa automáticamente.

---

## 🧪 Testes: Onde Ficam os Dados?

```python
# Testes usam SQLite em memória
# Localização: RAM (não em arquivo)

@pytest.fixture
def client():
    # Cria banco em memória
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Testes rodam com este banco
    # Ao finalizar → banco desaparece da RAM

# Resultado: Testes não deixam lixo! ✅
```

---

## 📋 Checklist: Tudo Pronto

- ✅ SQLite funcionando (sem Docker)
- ✅ `.\start.ps1` atualizado para detectar Docker
- ✅ `.env` configurado para SQLite local
- ✅ 6/6 testes passando
- ✅ Dados persistem em `usermanager.db`

---

## 🚀 Próximas Ações

### Agora:
```powershell
.\start.ps1
# Abra http://localhost:8000
# Crie alguns usuários
# Reinicie o servidor
# Veja que os dados continuam lá! ✨
```

### Depois (opcional):
```powershell
# Quando quiser usar Docker
# 1. Instale Docker Desktop
# 2. Execute start.ps1 novamente
# 3. Script detecta Docker automaticamente
```

---

## 📞 FAQ

**P: Por que o banco fica em usermanager.db?**
A: SQLite armazena tudo em um arquivo único. Fácil de backup, compartilhar, etc.

**P: Posso mover usermanager.db?**
A: Sim! É apenas um arquivo. Mas atualize DATABASE_URL no .env.

**P: Quanto espaço ocupa?**
A: Pequeno! ~1KB por usuário. 1000 usuários = ~1MB.

**P: E se deletar usermanager.db?**
A: Banco reseta. Próxima execução recria vazio. Tudo volta ao normal.

**P: Qual é melhor: SQLite ou PostgreSQL?**
A: 
- **SQLite**: Desenvolvimento rápido, sem dependências
- **PostgreSQL**: Produção, múltiplos usuários, mais robusto

**P: Pode usar em produção?**
A: SQLite sim, mas PostgreSQL é melhor. Depois da Missão 04 você muda facilmente.

---

## ✨ Resultado

**Agora você tem um projeto funcional que:**
- ✅ Persiste dados em disco (usermanager.db)
- ✅ Funciona sem Docker
- ✅ Consegue rodar `.\start.ps1`
- ✅ Todos os testes passam
- ✅ Pronto para próximas missões

**Quando quiser usar Docker depois:**
- Apenas instale Docker Desktop
- Execute `.\start.ps1`
- Script detecta automaticamente e usa PostgreSQL

🎉 **Missão 03 funcional com SQLite!**
