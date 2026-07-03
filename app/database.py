from __future__ import annotations

import csv
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from pathlib import Path
import sqlite3
from typing import Any, Iterator

from .risk import ResidentSnapshot, build_shift_digest, score_resident


SCHEMA = """
CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    room TEXT NOT NULL,
    condition TEXT NOT NULL,
    primary_contact TEXT NOT NULL,
    mobility TEXT NOT NULL,
    hydration_ml INTEGER NOT NULL,
    systolic INTEGER,
    diastolic INTEGER,
    pain_score INTEGER,
    glucose INTEGER,
    fall_risk INTEGER NOT NULL,
    mood TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER REFERENCES residents(id),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    name TEXT NOT NULL,
    dose TEXT NOT NULL,
    instructions TEXT NOT NULL,
    next_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled'
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER REFERENCES residents(id),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS family_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    name TEXT NOT NULL,
    relationship TEXT NOT NULL,
    phone TEXT NOT NULL,
    whatsapp TEXT NOT NULL,
    preference TEXT NOT NULL,
    emergency INTEGER NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    visitor_name TEXT NOT NULL,
    visit_at TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS care_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    focus TEXT NOT NULL,
    goal TEXT NOT NULL,
    routine TEXT NOT NULL,
    owner TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    specialty TEXT NOT NULL DEFAULT '',
    shift_start TEXT NOT NULL,
    shift_end TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    phone_extension TEXT NOT NULL DEFAULT ''
);
"""


@contextmanager
def connect(database_path: str) -> Iterator[sqlite3.Connection]:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def init_database(database_path: str, auto_seed: bool = True) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
        if auto_seed:
            seed_if_empty(connection)
            seed_support_tables_if_empty(connection)


def seed_if_empty(connection: sqlite3.Connection) -> None:
    existing = connection.execute("SELECT COUNT(*) FROM residents").fetchone()[0]
    if existing:
        return

    now = datetime.now().replace(microsecond=0).isoformat()
    residents = [
        (
            "Helena Matos",
            84,
            "B-12",
            "hipertensao e risco de queda",
            "Mariana Matos",
            "anda com apoio",
            880,
            168,
            98,
            3,
            112,
            8,
            "ansioso",
            now,
        ),
        (
            "Joao Ferreira",
            79,
            "A-04",
            "diabetes tipo 2",
            "Rafael Ferreira",
            "caminhada assistida",
            1460,
            132,
            82,
            1,
            128,
            4,
            "tranquilo",
            now,
        ),
        (
            "Lourdes Almeida",
            91,
            "C-08",
            "dor lombar cronica",
            "Beatriz Almeida",
            "cadeira de rodas",
            1040,
            146,
            88,
            8,
            98,
            6,
            "confuso",
            now,
        ),
        (
            "Sergio Paiva",
            87,
            "A-11",
            "pos-operatorio de quadril",
            "Patricia Paiva",
            "restricao parcial",
            1220,
            118,
            74,
            5,
            104,
            7,
            "calmo",
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO residents (
            name, age, room, condition, primary_contact, mobility, hydration_ml,
            systolic, diastolic, pain_score, glucose, fall_risk, mood, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        residents,
    )

    tasks = [
        (1, "Reavaliar pressao apos repouso", "sinais vitais", "08:30", "high", "pending"),
        (1, "Checar campainha e caminho livre", "seguranca", "09:00", "high", "pending"),
        (2, "Glicemia capilar antes do almoco", "sinais vitais", "11:20", "normal", "pending"),
        (2, "Caminhada assistida no jardim", "mobilidade", "15:30", "normal", "done"),
        (3, "Escala de dor e conforto postural", "dor", "10:00", "high", "pending"),
        (3, "Contato com familiar responsavel", "familia", "14:00", "normal", "pending"),
        (4, "Treino de transferencia com fisio", "reabilitacao", "13:30", "normal", "pending"),
    ]
    connection.executemany(
        """
        INSERT INTO tasks (resident_id, title, category, scheduled_at, priority, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        tasks,
    )

    medications = [
        (1, "Losartana", "50mg", "administrar apos afericao", "10:30", "scheduled"),
        (2, "Metformina", "850mg", "com refeicao", "11:00", "scheduled"),
        (3, "Dipirona", "500mg", "se dor persistir", "12:00", "scheduled"),
        (4, "Enoxaparina", "40mg", "conforme prescricao", "18:00", "scheduled"),
    ]
    connection.executemany(
        """
        INSERT INTO medications (resident_id, name, dose, instructions, next_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        medications,
    )

    events = [
        (1, "vital", "warning", "PA elevada em primeira afericao", now),
        (3, "pain", "high", "Relatou dor lombar intensa ao sentar", now),
        (4, "mobility", "normal", "Transferencia com boa tolerancia", now),
    ]
    connection.executemany(
        """
        INSERT INTO events (resident_id, event_type, severity, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        events,
    )
    connection.commit()


def seed_support_tables_if_empty(connection: sqlite3.Connection) -> None:
    contacts_existing = connection.execute("SELECT COUNT(*) FROM family_contacts").fetchone()[0]
    if not contacts_existing:
        family_contacts = [
            (1, "Mariana Matos", "filha", "(11) 98422-1408", "5511984221408", "WhatsApp apos 18h", 1, "Responsavel por autorizacoes."),
            (1, "Claudio Matos", "neto", "(11) 97310-4419", "5511973104419", "ligacao em urgencias", 0, "Pode acompanhar consultas."),
            (2, "Rafael Ferreira", "filho", "(21) 98840-7742", "5521988407742", "WhatsApp comercial", 1, "Enviar glicemias quando houver alteracao."),
            (3, "Beatriz Almeida", "sobrinha", "(31) 99125-6300", "5531991256300", "ligacao pela manha", 1, "Mora perto da unidade."),
            (4, "Patricia Paiva", "esposa", "(41) 99708-5126", "5541997085126", "WhatsApp a qualquer hora", 1, "Prefere resumo curto do plantao."),
        ]
        connection.executemany(
            """
            INSERT INTO family_contacts (
                resident_id, name, relationship, phone, whatsapp, preference, emergency, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            family_contacts,
        )

    visits_existing = connection.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    if not visits_existing:
        visits = [
            (1, "Mariana Matos", "Hoje 17:30", "confirmada", "Trazer cardigan e conversar sobre hidratacao."),
            (2, "Rafael Ferreira", "Amanha 10:00", "a confirmar", "Quer revisar dieta com enfermagem."),
            (3, "Beatriz Almeida", "Sexta 15:00", "confirmada", "Visita curta, evitar excesso de estimulo."),
            (4, "Patricia Paiva", "Hoje 19:00", "confirmada", "Atualizar evolucao da fisioterapia."),
        ]
        connection.executemany(
            """
            INSERT INTO visits (resident_id, visitor_name, visit_at, status, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            visits,
        )

    plans_existing = connection.execute("SELECT COUNT(*) FROM care_plans").fetchone()[0]
    if not plans_existing:
        care_plans = [
            (1, "Prevencao de queda", "Circular com apoio e campainha ao alcance", "Checar rota livre no inicio de cada turno", "Enfermagem"),
            (2, "Controle glicemico", "Manter glicemia pre-almoco registrada", "Reforcar refeicao completa antes da metformina", "Tecnico do turno"),
            (3, "Conforto e dor", "Reduzir dor para ate 4/10", "Reposicionamento a cada 2h e escala de dor", "Enfermagem"),
            (4, "Reabilitacao", "Melhorar transferencia cama-poltrona", "Treino assistido com fisioterapia", "Fisioterapia"),
        ]
        connection.executemany(
            """
            INSERT INTO care_plans (resident_id, focus, goal, routine, owner)
            VALUES (?, ?, ?, ?, ?)
            """,
            care_plans,
        )

    staff_existing = connection.execute("SELECT COUNT(*) FROM staff").fetchone()[0]
    if not staff_existing:
        staff = [
            ("Camila Nunes", "Enfermeira", "Enfermagem geriatrica", "07:00", "19:00", "active", "201"),
            ("Bruno Lima", "Enfermeiro", "Urgencia e emergencia", "07:00", "19:00", "active", "202"),
            ("Larissa Souza", "Enfermeira", "Cuidados paliativos", "19:00", "07:00", "scheduled", "203"),
            ("Dra. Ana Ribeiro", "Medica", "Geriatria", "08:00", "20:00", "active", "301"),
            ("Dr. Paulo Mendes", "Medico", "Clinica medica", "20:00", "08:00", "scheduled", "302"),
            ("Marcos Vieira", "Tecnico de enfermagem", "Ala A", "07:00", "19:00", "active", "211"),
        ]
        connection.executemany(
            """
            INSERT INTO staff (name, role, specialty, shift_start, shift_end, status, phone_extension)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            staff,
        )

    connection.commit()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def resident_snapshot(row: sqlite3.Row | dict[str, Any]) -> ResidentSnapshot:
    return ResidentSnapshot(
        name=row["name"],
        age=row["age"],
        systolic=row["systolic"],
        diastolic=row["diastolic"],
        pain_score=row["pain_score"],
        glucose=row["glucose"],
        fall_risk=row["fall_risk"],
        hydration_ml=row["hydration_ml"],
        mood=row["mood"],
    )


def resident_dict(row: sqlite3.Row) -> dict[str, Any]:
    resident = row_to_dict(row)
    resident["risk"] = score_resident(resident_snapshot(row))
    return resident


def list_residents(database_path: str) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute("SELECT * FROM residents ORDER BY room").fetchall()
    return [resident_dict(row) for row in rows]


def get_resident(database_path: str, resident_id: int) -> dict[str, Any] | None:
    with connect(database_path) as connection:
        row = connection.execute("SELECT * FROM residents WHERE id = ?", (resident_id,)).fetchone()
    return resident_dict(row) if row else None


def list_tasks(database_path: str, resident_id: int | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT tasks.*, residents.name AS resident_name, residents.room AS room
        FROM tasks
        LEFT JOIN residents ON residents.id = tasks.resident_id
    """
    params: tuple[Any, ...] = ()
    if resident_id is not None:
        query += " WHERE tasks.resident_id = ?"
        params = (resident_id,)
    query += " ORDER BY scheduled_at"
    with connect(database_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [row_to_dict(row) for row in rows]


def list_medications(database_path: str, resident_id: int | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT medications.*, residents.name AS resident_name, residents.room AS room
        FROM medications
        JOIN residents ON residents.id = medications.resident_id
    """
    params: tuple[Any, ...] = ()
    if resident_id is not None:
        query += " WHERE medications.resident_id = ?"
        params = (resident_id,)
    query += " ORDER BY next_at"
    with connect(database_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [row_to_dict(row) for row in rows]


def list_events(database_path: str, resident_id: int | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT events.*, residents.name AS resident_name
        FROM events
        LEFT JOIN residents ON residents.id = events.resident_id
    """
    params: tuple[Any, ...] = ()
    if resident_id is not None:
        query += " WHERE events.resident_id = ?"
        params = (resident_id,)
    query += " ORDER BY created_at DESC, id DESC LIMIT 12"
    with connect(database_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [row_to_dict(row) for row in rows]


def list_family_contacts(database_path: str, resident_id: int | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT family_contacts.*, residents.name AS resident_name, residents.room AS room
        FROM family_contacts
        JOIN residents ON residents.id = family_contacts.resident_id
    """
    params: tuple[Any, ...] = ()
    if resident_id is not None:
        query += " WHERE family_contacts.resident_id = ?"
        params = (resident_id,)
    query += " ORDER BY family_contacts.emergency DESC, residents.room, family_contacts.name"
    with connect(database_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [row_to_dict(row) for row in rows]


def list_visits(database_path: str) -> list[dict[str, Any]]:
    query = """
        SELECT visits.*, residents.name AS resident_name, residents.room AS room
        FROM visits
        JOIN residents ON residents.id = visits.resident_id
        ORDER BY visits.id
    """
    with connect(database_path) as connection:
        rows = connection.execute(query).fetchall()
    return [row_to_dict(row) for row in rows]


def list_care_plans(database_path: str) -> list[dict[str, Any]]:
    query = """
        SELECT care_plans.*, residents.name AS resident_name, residents.room AS room
        FROM care_plans
        JOIN residents ON residents.id = care_plans.resident_id
        ORDER BY residents.room
    """
    with connect(database_path) as connection:
        rows = connection.execute(query).fetchall()
    return [row_to_dict(row) for row in rows]


def list_staff(database_path: str, status: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM staff"
    params: tuple[Any, ...] = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY CASE role WHEN 'Medica' THEN 1 WHEN 'Medico' THEN 1 WHEN 'Enfermeira' THEN 2 WHEN 'Enfermeiro' THEN 2 ELSE 3 END, name"
    with connect(database_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [row_to_dict(row) for row in rows]


def dashboard(database_path: str) -> dict[str, Any]:
    residents = list_residents(database_path)
    tasks = list_tasks(database_path)
    medications = list_medications(database_path)
    events = list_events(database_path)
    family_contacts = list_family_contacts(database_path)
    visits = list_visits(database_path)
    care_plans = list_care_plans(database_path)
    staff = list_staff(database_path)
    active_staff = [member for member in staff if member["status"] == "active"]
    active_nurses = [member for member in active_staff if member["role"] in {"Enfermeira", "Enfermeiro"}]
    doctors_on_duty = [member for member in active_staff if member["role"] in {"Medica", "Medico"}]
    pending_tasks = [task for task in tasks if task["status"] != "done"]
    due_meds = [med for med in medications if med["status"] != "given"]
    high_risk = [resident for resident in residents if resident["risk"]["level"] == "critico"]
    watch = [resident for resident in residents if resident["risk"]["level"] == "observacao"]
    emergency_contacts = [contact for contact in family_contacts if contact["emergency"]]

    return {
        "metrics": {
            "residents": len(residents),
            "critical": len(high_risk),
            "watch": len(watch),
            "pending_tasks": len(pending_tasks),
            "due_meds": len(due_meds),
            "family_contacts": len(family_contacts),
            "emergency_contacts": len(emergency_contacts),
            "active_nurses": len(active_nurses),
            "doctors_on_duty": len(doctors_on_duty),
        },
        "residents": residents,
        "tasks": tasks,
        "medications": medications,
        "events": events,
        "family_contacts": family_contacts,
        "visits": visits,
        "care_plans": care_plans,
        "staff": staff,
        "active_staff": active_staff,
        "active_nurses": active_nurses,
        "doctors_on_duty": doctors_on_duty,
    }


def toggle_task(database_path: str, task_id: int) -> dict[str, Any] | None:
    with connect(database_path) as connection:
        row = connection.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        next_status = "pending" if row["status"] == "done" else "done"
        connection.execute("UPDATE tasks SET status = ? WHERE id = ?", (next_status, task_id))
        connection.commit()
    return next(task for task in list_tasks(database_path) if task["id"] == task_id)


def create_event(
    database_path: str,
    resident_id: int | None,
    event_type: str,
    severity: str,
    note: str,
) -> dict[str, Any]:
    created_at = datetime.now().replace(microsecond=0).isoformat()
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO events (resident_id, event_type, severity, note, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (resident_id, event_type, severity, note, created_at),
        )
        connection.commit()
        row = connection.execute(
            """
            SELECT events.*, residents.name AS resident_name
            FROM events
            LEFT JOIN residents ON residents.id = events.resident_id
            WHERE events.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return row_to_dict(row)


def resident_digest(database_path: str, resident_id: int) -> dict[str, Any] | None:
    resident = get_resident(database_path, resident_id)
    if not resident:
        return None
    tasks = list_tasks(database_path, resident_id)
    medications = list_medications(database_path, resident_id)
    events = list_events(database_path, resident_id)
    contacts = list_family_contacts(database_path, resident_id)
    digest = build_shift_digest(resident, resident["risk"], tasks, medications, events)
    if contacts:
        primary = contacts[0]
        digest["actions"].append(
            f"familiar de referencia: {primary['name']} ({primary['relationship']}) - {primary['phone']}"
        )
    return digest


def export_residents_csv(database_path: str) -> str:
    residents = list_residents(database_path)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "name",
            "age",
            "room",
            "condition",
            "risk_level",
            "risk_score",
            "primary_contact",
            "updated_at",
        ]
    )
    for resident in residents:
        writer.writerow(
            [
                resident["id"],
                resident["name"],
                resident["age"],
                resident["room"],
                resident["condition"],
                resident["risk"]["level"],
                resident["risk"]["score"],
                resident["primary_contact"],
                resident["updated_at"],
            ]
        )
    return output.getvalue()
