# Como Rodar o Projeto - Missão 03

## ⚡ Primeira vez? Comece aqui

### 1. Tenha Docker instalado
O PostgreSQL roda dentro do Docker. Baixe e instale:
- **[Docker Desktop](https://www.docker.com/products/docker-desktop)**

### 2. Clone e entre no projeto
```bash
git clone https://github.com/Claude-Impact-Lab/bootcamp-tech-afya.git
cd bootcamp-tech-afya
```

### 3. Rode o script de inicialização

**No Windows (PowerShell):**
```powershell
.\start.ps1
```

**No Mac/Linux:**
```bash
./start.sh  # (em breve - por enquanto, veja os passos manuais abaixo)
```

Pronto! O servidor estará em [http://localhost:8000](http://localhost:8000)

---

## 🔧 Passos Manuais (se preferir não usar o script)

### 1. Subir o PostgreSQL com Docker
```bash
docker-compose up -d
```

Verificar que está pronto:
```bash
docker-compose ps
```

Deve mostrar `usermanager-postgres` com status `Up`.

### 2. Sincronizar dependências
```bash
uv sync
```

### 3. Iniciar o servidor
```bash
uv run uvicorn app.main:app --reload
```

Acesse [http://localhost:8000](http://localhost:8000)

---

## 📋 Comandos úteis

### Rodar os testes
```bash
uv run pytest
```

### Acessar o banco PostgreSQL diretamente
```bash
docker-compose exec postgres psql -U user -d usermanager
```

Dentro do `psql`, você pode:
```sql
\dt              -- listar tabelas
SELECT * FROM users;  -- ver usuários
\q              -- sair
```

### Parar o PostgreSQL
```bash
docker-compose down
```

### Parar e limpar tudo (incluindo dados)
```bash
docker-compose down -v
```

---

## 📝 Variáveis de Ambiente

O arquivo `.env` contém as credenciais do banco:
```env
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=usermanager
DATABASE_URL=postgresql://user:password@localhost:5432/usermanager
```

**⚠️ Importante:** `.env` não vai para o Git (veja no `.gitignore`). Use `.env.example` como referência.

---

## 🎯 O que mudou nesta missão

1. **Banco de dados real:** Dados agora persistem quando você reinicia o servidor
2. **SQLAlchemy:** O código usa um ORM para conversar com o banco
3. **Docker:** PostgreSQL roda isolado em um container
4. **Migrações:** Próximo passo será versionar a estrutura das tabelas
5. **Testes isolados:** Cada teste usa seu próprio banco em memória

---

## ❓ Problemas comuns

**"Docker não está rodando"**
- Abra o Docker Desktop e aguarde estar pronto

**"Connection refused"**
- Aguarde alguns segundos - PostgreSQL pode estar iniciando
- Verifique com `docker-compose ps`

**"Module not found"**
- Execute `uv sync` para baixar as dependências novas

---

Pronto! Agora você tem um banco de dados de verdade! 🚀
