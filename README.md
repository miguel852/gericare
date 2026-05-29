# GeriCare

GeriCare e um painel operacional em Python para cuidado geriatrico: residentes, tarefas do plantao, medicacoes, eventos clinicos, resumo automatico e exportacao CSV.

## Rodar com Docker

```bash
docker compose up --build
```

Depois abra:

```text
http://localhost:8000
```

Os dados ficam persistidos em um volume Docker chamado `gericare_data`.

## Publicar no GitHub e hospedar

Este projeto ja esta pronto para deploy Docker e inclui `render.yaml` para Render.

### GitHub

```bash
git init
git add .
git commit -m "Initial GeriCare app"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/gericare.git
git push -u origin main
```

### Render

1. Crie um novo repositorio no GitHub e envie o codigo.
2. No Render, escolha **New > Blueprint**.
3. Conecte o repositorio `gericare`.
4. Confirme o Blueprint encontrado em `render.yaml`.
5. Depois do deploy, abra a URL `onrender.com` gerada pelo Render.

O `render.yaml` monta um disco persistente em `/app/data`, define o SQLite em
`/app/data/gericare.sqlite3` e deixa o seed inicial ligado.

## Rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

No Windows, tambem da para usar o atalho:

```powershell
.\run.ps1
```

## Testes

```bash
python -m unittest discover -s tests
```

## Recursos incluidos

- FastAPI com templates Jinja2.
- SQLite persistente com seed automatico.
- Dashboard responsivo para plantao.
- Motor de risco clinico simples e testavel.
- Resumo automatico por residente.
- Registro rapido de eventos.
- Exportacao CSV dos residentes.
- Dockerfile, Docker Compose, healthcheck e `.env.example`.
- PWA basico com cache de assets estaticos.

## Endpoints uteis

```text
GET  /health
GET  /api/dashboard
GET  /api/residents
GET  /api/residents/{resident_id}/digest
POST /api/tasks/{task_id}/toggle
POST /api/events
GET  /api/export/residents.csv
```
