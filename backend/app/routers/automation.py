import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from app.automation.browser import create_browser
from app.automation.engine import login, run_automation_for_cota

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])

# Manter referência global do driver para fechar o navegador quando solicitado
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


def _parse_cota_item(bid: BidQuotaSchema) -> Optional[Dict[str, str]]:
    """Converte BidQuotaSchema para o formato cota_info {'grupo', 'cota', 'digito', 'original'}."""
    if bid.grupo and bid.cota and bid.digito:
        return {
            "grupo": str(bid.grupo).strip(),
            "cota": str(bid.cota).strip(),
            "digito": str(bid.digito).strip(),
            "original": f"{bid.grupo}.{bid.cota}-{bid.digito}",
        }
    if bid.quota:
        partes = [p.strip() for p in str(bid.quota).replace(".", ",").replace("-", ",").split(",") if p.strip()]
        if len(partes) == 3:
            return {
                "grupo": partes[0],
                "cota": partes[1],
                "digito": partes[2],
                "original": str(bid.quota),
            }
    return None


def _run_browser_automation(config: AutomationConfigSchema):
    global _current_driver
    try:
        logger.info(f"[AUTOMAÇÃO] Criando e abrindo o Firefox para o consultor: {config.consultantName}")
        _current_driver = create_browser()

        # Efetua login no site do Servopa
        logger.info("[AUTOMAÇÃO] Efetuando login no portal Servopa...")
        login(_current_driver)
        logger.info("[AUTOMAÇÃO] Login concluído com sucesso. Navegador visível na tela!")

        # Processa cada cota recebida
        if config.bids:
            for bid in config.bids:
                if _current_driver is None:
                    logger.info("[AUTOMAÇÃO] Execução interrompida pelo usuário.")
                    break

                cota_info = _parse_cota_item(bid)
                if not cota_info:
                    logger.warning(f"[AUTOMAÇÃO] Cota ignorada (formato inválido): {bid}")
                    continue

                logger.info(f"[AUTOMAÇÃO] Processando cota: {cota_info['original']}")
                status, msg = run_automation_for_cota(_current_driver, cota_info, config.consultantName)
                logger.info(f"[AUTOMAÇÃO] Resultado da cota {cota_info['original']}: {status} - {msg}")

    except Exception as e:
        logger.error(f"[AUTOMAÇÃO ERRO] Falha durante a execução da automação: {e}", exc_info=True)
        # Mantém o driver se ainda estiver aberto para que o usuário possa visualizar
        if _current_driver is None:
            logger.error("[AUTOMAÇÃO ERRO] O navegador não pôde ser iniciado.")


@router.post("/start")
def start_automation(
    config: AutomationConfigSchema,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    print(f"[AUTOMAÇÃO] Solicitação recebida para o consultor: {config.consultantName}")
    background_tasks.add_task(_run_browser_automation, config)
    return {
        "status": "running",
        "message": "Automação iniciada com sucesso. Abrindo o navegador Firefox...",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/stop")
def stop_automation() -> Dict[str, Any]:
    global _current_driver
    print("[AUTOMAÇÃO] Solicitação recebida para fechar o navegador e parar a automação...")
    if _current_driver is not None:
        try:
            _current_driver.quit()
            print("[AUTOMAÇÃO] Navegador Firefox encerrado com sucesso.")
        except Exception as e:
            print(f"[AUTOMAÇÃO AVISO] Erro ao fechar o navegador: {e}")
        finally:
            _current_driver = None
    else:
        print("[AUTOMAÇÃO] Nenhum navegador ativo para encerrar.")

    return {
        "status": "idle",
        "message": "Automação encerrada e navegador fechado.",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
def get_automation_status() -> Dict[str, Any]:
    return {
        "status": "running" if _current_driver is not None else "idle",
        "message": "Automação em execução" if _current_driver is not None else "Aguardando início",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.websocket("/live")
async def automation_live_view(websocket: WebSocket) -> None:
    """Transmite screenshots periódicas do navegador em execução para o frontend.

    Cada cliente conectado recebe, a cada ~1s, um frame JPEG/PNG em base64
    (via `driver.get_screenshot_as_base64`) enquanto a automação estiver
    rodando, ou um status 'idle' caso nenhum navegador esteja aberto.
    A captura roda em threadpool pois o Selenium é síncrono/bloqueante.
    """
    await websocket.accept()
    logger.info("[LIVE VIEW] Cliente conectado.")
    try:
        while True:
            driver = _current_driver
            if driver is not None:
                try:
                    frame = await run_in_threadpool(driver.get_screenshot_as_base64)
                    await websocket.send_json({"type": "frame", "image": frame})
                except Exception as e:
                    logger.warning(f"[LIVE VIEW] Falha ao capturar tela: {e}")
                    await websocket.send_json({"type": "status", "status": "unavailable"})
            else:
                await websocket.send_json({"type": "status", "status": "idle"})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("[LIVE VIEW] Cliente desconectado.")
