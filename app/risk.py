from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResidentSnapshot:
    name: str
    age: int
    systolic: int | None
    diastolic: int | None
    pain_score: int | None
    glucose: int | None
    fall_risk: int
    hydration_ml: int
    mood: str


def score_resident(snapshot: ResidentSnapshot) -> dict[str, Any]:
    score = 0
    reasons: list[str] = []

    if snapshot.age >= 85:
        score += 8
        reasons.append("idade avancada")

    if snapshot.systolic is not None and snapshot.diastolic is not None:
        if snapshot.systolic >= 170 or snapshot.diastolic >= 105:
            score += 28
            reasons.append("pressao muito elevada")
        elif snapshot.systolic >= 150 or snapshot.diastolic >= 95:
            score += 18
            reasons.append("pressao em observacao")
        elif snapshot.systolic < 95:
            score += 20
            reasons.append("pressao baixa")

    if snapshot.pain_score is not None:
        if snapshot.pain_score >= 8:
            score += 18
            reasons.append("dor intensa")
        elif snapshot.pain_score >= 5:
            score += 10
            reasons.append("dor moderada")

    if snapshot.glucose is not None:
        if snapshot.glucose < 70:
            score += 24
            reasons.append("hipoglicemia possivel")
        elif snapshot.glucose >= 220:
            score += 18
            reasons.append("glicemia alta")
        elif snapshot.glucose >= 160:
            score += 8
            reasons.append("glicemia em acompanhamento")

    if snapshot.fall_risk >= 8:
        score += 18
        reasons.append("risco de queda alto")
    elif snapshot.fall_risk >= 5:
        score += 10
        reasons.append("risco de queda moderado")

    if snapshot.hydration_ml < 900:
        score += 14
        reasons.append("hidratacao baixa")
    elif snapshot.hydration_ml < 1300:
        score += 7
        reasons.append("reforcar hidratacao")

    if snapshot.mood.lower() in {"confuso", "agitado", "ansioso"}:
        score += 10
        reasons.append(f"humor {snapshot.mood.lower()}")

    score = min(score, 100)
    if score >= 70:
        level = "critico"
    elif score >= 42:
        level = "observacao"
    else:
        level = "estavel"

    return {
        "score": score,
        "level": level,
        "reasons": reasons or ["sem sinais de prioridade clinica"],
        "actions": recommended_actions(level, reasons),
    }


def recommended_actions(level: str, reasons: list[str]) -> list[str]:
    actions = []
    if level == "critico":
        actions.append("acionar enfermagem lider e registrar reavaliacao em ate 15 minutos")
    elif level == "observacao":
        actions.append("monitorar sinais e revisar plano do turno")
    else:
        actions.append("manter rotina e registrar evolucao normal")

    if any("pressao" in reason for reason in reasons):
        actions.append("confirmar medida apos repouso e checar medicacao anti-hipertensiva")
    if any("queda" in reason for reason in reasons):
        actions.append("revisar rota de caminhada, campainha e calcado")
    if any("glicemia" in reason or "hipoglicemia" in reason for reason in reasons):
        actions.append("validar refeicao, glicemia capilar e conduta prescrita")
    if any("hidratacao" in reason for reason in reasons):
        actions.append("oferecer liquidos fracionados e acompanhar aceitacao")
    if any("dor" in reason for reason in reasons):
        actions.append("aplicar escala de dor e verificar analgesia prescrita")
    return actions


def build_shift_digest(
    resident: dict[str, Any],
    risk: dict[str, Any],
    tasks: list[dict[str, Any]],
    medications: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    pending_tasks = [task for task in tasks if task["status"] != "done"]
    next_meds = [med for med in medications if med["status"] != "given"]
    recent_events = events[:3]

    summary = [
        f"{resident['name']}, {resident['age']} anos, quarto {resident['room']}.",
        f"Nivel atual: {risk['level']} ({risk['score']}/100).",
        "Motivos: " + ", ".join(risk["reasons"]) + ".",
    ]

    if pending_tasks:
        summary.append("Pendencias: " + "; ".join(task["title"] for task in pending_tasks[:3]) + ".")
    if next_meds:
        summary.append(
            "Proximas medicacoes: "
            + "; ".join(f"{med['name']} {med['dose']} as {med['next_at']}" for med in next_meds[:3])
            + "."
        )
    if recent_events:
        summary.append("Eventos recentes: " + "; ".join(event["note"] for event in recent_events) + ".")

    return {
        "resident_id": resident["id"],
        "headline": f"Plantao de {resident['name']}",
        "summary": " ".join(summary),
        "actions": risk["actions"],
    }
