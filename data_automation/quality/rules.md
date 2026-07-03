# Regras de Qualidade

## Residentes

- `resident_id` deve existir.
- `name` nao pode estar vazio.
- `room` nao pode estar vazio.
- `age` deve ficar entre 60 e 115.

## Sinais vitais

- `systolic` deve ficar entre 80 e 220.
- `diastolic` deve ficar entre 40 e 130.
- `pain_score` deve ficar entre 0 e 10.
- Registros duplicados por `resident_id` e `measured_at` sao removidos.

## Negocio

- `risk_level = critico` quando `risk_score >= 7`.
- `risk_level = observacao` quando `risk_score >= 4`.
- `risk_level = estavel` quando `risk_score < 4`.

