from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.automation.browser import create_browser

router = APIRouter(prefix="/automation", tags=["automation"])

# Manter referência global do driver para evitar que seja coletado pelo garbage collector
_current_driver = None


class BidQuotaSchema(BaseModel):
    id: Optional[str] = None
    grupo: Optional[str] = None
    cota: Optional[str] = None
    digito: Optional[str] = None
    quota: Optional[str] = None
    bidValue: Optional[str] = None


class AutomationConfigSchema(BaseModel):
    consultantName: str
    bids: Optional[List[BidQuotaSchema]] = []


def _run_browser_automation():
    global _current_driver
    try:
        print("[AUTOMAÇÃO] Criando e abrindo o Firefox via Selenium...")
        _current_driver = create_browser()
        _current_driver.get("https://www.google.com")
        print(f"[AUTOMAÇÃO] Firefox aberto com sucesso! Título: {_current_driver.title}")
    except Exception as e:
        print(f"[AUTOMAÇÃO ERRO] Falha ao abrir o Firefox: {e}")


@router.post("/start")
def start_automation(
    config: AutomationConfigSchema,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    print(f"[AUTOMAÇÃO] Solicitação recebida para o consultor: {config.consultantName}")
    background_tasks.add_task(_run_browser_automation)
    return {
        "status": "running",
        "message": "Automação iniciada com sucesso. Abrindo o navegador Firefox...",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/stop")
def stop_automation() -> Dict[str, Any]:
    global _current_driver
    if _current_driver:
        try:
            _current_driver.quit()
        except Exception:
            pass
        _current_driver = None
    return {
        "status": "idle",
        "message": "Automação encerrada.",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
def get_automation_status() -> Dict[str, Any]:
    return {
        "status": "running" if _current_driver is not None else "idle",
        "message": "Automação em execução" if _current_driver is not None else "Aguardando início",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
