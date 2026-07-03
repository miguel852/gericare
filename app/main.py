from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import database
from .settings import BASE_DIR, get_settings


class EventIn(BaseModel):
    resident_id: int | None = None
    event_type: str = Field(default="note", min_length=2, max_length=40)
    severity: str = Field(default="normal", pattern="^(normal|warning|high)$")
    note: str = Field(min_length=3, max_length=280)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    database.init_database(settings.database_path, settings.auto_seed)
    yield


app = FastAPI(title="GeriCare", version="1.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


def render_page(request: Request, page: str, title: str):
    settings = get_settings()
    data = database.dashboard(settings.database_path)
    context = {
        "request": request,
        "facility_name": settings.facility_name,
        "page": page,
        "page_title": title,
        **data,
    }
    try:
        return templates.TemplateResponse(request=request, name="dashboard.html", context=context)
    except TypeError:
        # Compatibilidade com Starlette anterior a 0.29.
        return templates.TemplateResponse("dashboard.html", context)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return render_page(request, "dashboard", "Visao geral")


@app.get("/residentes", response_class=HTMLResponse)
async def residents_page(request: Request):
    return render_page(request, "residents", "Residentes")


@app.get("/plantao", response_class=HTMLResponse)
async def shift_page(request: Request):
    return render_page(request, "shift", "Plantao")


@app.get("/medicacoes", response_class=HTMLResponse)
async def medications_page(request: Request):
    return render_page(request, "medications", "Medicacoes")


@app.get("/familiares", response_class=HTMLResponse)
async def family_page(request: Request):
    return render_page(request, "family", "Familiares e visitas")


@app.get("/cuidados", response_class=HTMLResponse)
async def care_page(request: Request):
    return render_page(request, "care", "Planos de cuidado")


@app.get("/equipe", response_class=HTMLResponse)
async def staff_page(request: Request):
    return render_page(request, "staff", "Equipe de plantao")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gericare"}


@app.get("/api/dashboard")
async def api_dashboard():
    settings = get_settings()
    return database.dashboard(settings.database_path)


@app.get("/api/residents")
async def api_residents():
    settings = get_settings()
    return database.list_residents(settings.database_path)


@app.get("/api/family-contacts")
async def api_family_contacts():
    settings = get_settings()
    return database.list_family_contacts(settings.database_path)


@app.get("/api/visits")
async def api_visits():
    settings = get_settings()
    return database.list_visits(settings.database_path)


@app.get("/api/staff")
async def api_staff(status: str | None = None):
    settings = get_settings()
    return database.list_staff(settings.database_path, status)


@app.get("/api/residents/{resident_id}/digest")
async def api_resident_digest(resident_id: int):
    settings = get_settings()
    digest = database.resident_digest(settings.database_path, resident_id)
    if digest is None:
        raise HTTPException(status_code=404, detail="Resident not found")
    return digest


@app.post("/api/tasks/{task_id}/toggle")
async def api_toggle_task(task_id: int):
    settings = get_settings()
    task = database.toggle_task(settings.database_path, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/api/events", status_code=201)
async def api_create_event(event: EventIn):
    settings = get_settings()
    if event.resident_id and not database.get_resident(settings.database_path, event.resident_id):
        raise HTTPException(status_code=404, detail="Resident not found")
    return database.create_event(
        settings.database_path,
        event.resident_id,
        event.event_type,
        event.severity,
        event.note,
    )


@app.get("/api/export/residents.csv")
async def api_export_residents():
    settings = get_settings()
    csv_content = database.export_residents_csv(settings.database_path)
    headers = {"Content-Disposition": 'attachment; filename="gericare-residents.csv"'}
    return Response(content=csv_content, media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/{path:path}", include_in_schema=False)
async def not_found(path: str):
    raise HTTPException(status_code=404, detail="Pagina nao encontrada")
