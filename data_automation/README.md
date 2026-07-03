# GeriCare Data Automation

Projeto de automacao de dados para tratamento de planilhas operacionais do GeriCare.

Ele simula um fluxo real de engenharia de dados para uma instituicao de cuidado geriatrico:
planilhas de residentes, sinais vitais, medicacoes e tarefas entram como CSV/Excel-like,
sao padronizadas com Spark, passam por validacoes de qualidade e geram bases finais para
dashboard, acompanhamento de risco e comunicacao com familiares.

## Arquitetura

```text
input/*.csv
   |
   v
Bronze: leitura bruta das planilhas
   |
   v
Silver: limpeza, tipos, deduplicacao e regras de negocio
   |
   v
Gold: indicadores e datasets finais
```

## Saidas geradas

- `output/silver/residents`: residentes limpos e padronizados.
- `output/silver/vitals`: sinais vitais tratados.
- `output/silver/medications`: medicacoes normalizadas.
- `output/silver/tasks`: tarefas higienizadas.
- `output/gold/resident_risk_summary`: score operacional por residente.
- `output/gold/shift_board`: quadro consolidado do plantao.
- `output/gold/family_follow_up`: contatos e alertas para familiares.
- `output/quality/quality_report.csv`: resumo das validacoes.

## Rodar localmente com Docker

```bash
cd data_automation
docker compose up --build
```

O container executa:

```bash
python src/generate_sample_data.py
spark-submit src/pipeline.py --input input --output output
python src/validate_outputs.py --output output
```

## Rodar sem Docker

Requer Java e Python 3.11+.

```bash
cd data_automation
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/generate_sample_data.py
python src/pipeline.py --input input --output output
python src/validate_outputs.py --output output
```

No Windows, a execucao local do Spark pode exigir `HADOOP_HOME` e `winutils.exe`.
Para evitar essa configuracao manual, prefira Docker ou Databricks.

## Databricks

Use `notebooks/databricks_gericare_pipeline.py` em um workspace Databricks.

Sugestao para portfolio:

1. Crie um cluster com runtime Spark.
2. Suba os arquivos CSV da pasta `input/` para DBFS ou Unity Catalog volume.
3. Ajuste as variaveis `INPUT_PATH` e `OUTPUT_PATH` no notebook.
4. Execute as celulas e publique prints das tabelas gold.

## Regras de negocio

- Residentes sem nome, quarto ou idade valida sao marcados no relatorio de qualidade.
- Sinais vitais fora de faixa sao sinalizados para revisao.
- Score de risco combina idade, pressao, dor, glicemia, hidratacao e risco de queda.
- Tarefas atrasadas e medicacoes pendentes aparecem no quadro do plantao.
- Alertas de familiar priorizam residentes em observacao ou criticos.

## Texto curto para LinkedIn

Criei um projeto de automacao de dados para o GeriCare usando Python, Spark, Docker e
Databricks. O pipeline trata planilhas operacionais de cuidado geriatrico, aplica regras de
qualidade, calcula risco por residente e gera bases finais para dashboard de plantao e
acompanhamento familiar. A arquitetura segue camadas bronze, silver e gold, com execucao
local via Docker e notebook pronto para Databricks.
