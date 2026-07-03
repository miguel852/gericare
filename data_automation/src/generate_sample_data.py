from __future__ import annotations

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = BASE_DIR / "input"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    residents = [
        {
            "resident_id": 1,
            "name": "Helena Matos",
            "age": 84,
            "room": "B-12",
            "condition": "hipertensao e risco de queda",
            "primary_contact": "Mariana Matos",
            "contact_phone": "5511984221408",
            "mobility": "anda com apoio",
            "fall_risk": 8,
            "updated_at": "2026-06-01 08:00:00",
        },
        {
            "resident_id": 2,
            "name": "Joao Ferreira",
            "age": 79,
            "room": "A-04",
            "condition": "diabetes tipo 2",
            "primary_contact": "Rafael Ferreira",
            "contact_phone": "5521988407742",
            "mobility": "caminhada assistida",
            "fall_risk": 4,
            "updated_at": "2026-06-01 08:00:00",
        },
        {
            "resident_id": 3,
            "name": "Lourdes Almeida",
            "age": 91,
            "room": "C-08",
            "condition": "dor lombar cronica",
            "primary_contact": "Beatriz Almeida",
            "contact_phone": "5531991256300",
            "mobility": "cadeira de rodas",
            "fall_risk": 6,
            "updated_at": "2026-06-01 08:00:00",
        },
        {
            "resident_id": 4,
            "name": "Sergio Paiva",
            "age": 87,
            "room": "A-11",
            "condition": "pos-operatorio de quadril",
            "primary_contact": "Patricia Paiva",
            "contact_phone": "5541997085126",
            "mobility": "restricao parcial",
            "fall_risk": 7,
            "updated_at": "2026-06-01 08:00:00",
        },
    ]

    vitals = [
        {"resident_id": 1, "measured_at": "2026-06-01 08:10:00", "systolic": 168, "diastolic": 98, "glucose": 112, "pain_score": 3, "hydration_ml": 880},
        {"resident_id": 1, "measured_at": "2026-06-01 14:10:00", "systolic": 154, "diastolic": 90, "glucose": 118, "pain_score": 2, "hydration_ml": 1250},
        {"resident_id": 2, "measured_at": "2026-06-01 08:20:00", "systolic": 132, "diastolic": 82, "glucose": 128, "pain_score": 1, "hydration_ml": 1460},
        {"resident_id": 3, "measured_at": "2026-06-01 08:30:00", "systolic": 146, "diastolic": 88, "glucose": 98, "pain_score": 8, "hydration_ml": 1040},
        {"resident_id": 4, "measured_at": "2026-06-01 08:40:00", "systolic": 118, "diastolic": 74, "glucose": 104, "pain_score": 5, "hydration_ml": 1220},
    ]

    medications = [
        {"resident_id": 1, "medication": "Losartana", "dose": "50mg", "scheduled_at": "2026-06-01 10:30:00", "status": "scheduled"},
        {"resident_id": 2, "medication": "Metformina", "dose": "850mg", "scheduled_at": "2026-06-01 11:00:00", "status": "given"},
        {"resident_id": 3, "medication": "Dipirona", "dose": "500mg", "scheduled_at": "2026-06-01 12:00:00", "status": "scheduled"},
        {"resident_id": 4, "medication": "Enoxaparina", "dose": "40mg", "scheduled_at": "2026-06-01 18:00:00", "status": "scheduled"},
    ]

    tasks = [
        {"resident_id": 1, "task": "Reavaliar pressao apos repouso", "category": "sinais vitais", "scheduled_at": "2026-06-01 08:30:00", "priority": "high", "status": "pending"},
        {"resident_id": 1, "task": "Checar campainha e caminho livre", "category": "seguranca", "scheduled_at": "2026-06-01 09:00:00", "priority": "high", "status": "pending"},
        {"resident_id": 2, "task": "Glicemia capilar antes do almoco", "category": "sinais vitais", "scheduled_at": "2026-06-01 11:20:00", "priority": "normal", "status": "pending"},
        {"resident_id": 3, "task": "Escala de dor e conforto postural", "category": "dor", "scheduled_at": "2026-06-01 10:00:00", "priority": "high", "status": "pending"},
        {"resident_id": 4, "task": "Treino de transferencia com fisio", "category": "reabilitacao", "scheduled_at": "2026-06-01 13:30:00", "priority": "normal", "status": "done"},
    ]

    write_csv(INPUT_DIR / "residents.csv", residents)
    write_csv(INPUT_DIR / "vitals.csv", vitals)
    write_csv(INPUT_DIR / "medications.csv", medications)
    write_csv(INPUT_DIR / "tasks.csv", tasks)
    print(f"Sample spreadsheets written to {INPUT_DIR}")


if __name__ == "__main__":
    main()

