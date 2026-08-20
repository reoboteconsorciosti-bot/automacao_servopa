import asyncio
import os
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from app.automation.browser import check_automation_environment, create_browser
from app.automation.engine import login, run_automation_for_cota, salvar_log_erros
from app.database import engine, Base, SessionLocal
from app.models.automation_history import AutomationHistory
from app.models.pdf_document import PdfDocument

logger = logging.getLogger(__name__)

# Garante a criação da tabela automation_history no PostgreSQL se ainda não existir
try:
    Base.metadata.create_all(bind=engine)
except Exception as _e:
    logger.warning(f"Erro ao sincronizar tabelas no banco de dados: {_e}")

router = APIRouter(prefix="/api/automation", tags=["automation"])

# Manter referência global do driver para fechar o navegador quando solicitado
_current_driver = None
_current_history_id = None
# Progresso por cota da execução em andamento — lista de
# {"quota": str, "status": "pendente"|"processando"|"SUCESSO"|"ERRO_BENIGNO"|"ERRO_CRITICO"|"invalido", "message": str|None}
_current_progress: List[Dict[str, Any]] = []
# Resultado da última execução concluída (driver já fechado): "idle" | "finished" | "error".
# É o que diferencia "terminou processando tudo certo" de "travou/crashou antes de terminar" —
# sem isso, o frontend não teria como saber por que o navegador fechou.
_current_final_status: str = "idle"


class BidQuotaSchema(BaseModel):
    id: Optional[str] = None
    grupo: Optional[str] = None
    cota: Optional[str] = None
    digito: Optional[str] = None
    quota: Optional[str] = None
    bidValue: Optional[str] = None


class AutomationConfigSchema(BaseModel):
    consultantName: str
    userName: Optional[str] = None
    userEmail: Optional[str] = None
    bids: Optional[List[BidQuotaSchema]] = []


class HistoryOutSchema(BaseModel):
    id: str
    executedBy: Dict[str, Any]
    consultantName: str
    quotasCount: int
    quotasSummary: str
    createdAt: str
    status: str
    pdfFilename: Optional[str] = None


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


def _save_pdf_to_db(
    consultant_name: str,
    quota: Optional[str],
    pdf_path: str,
    history_id: Optional[int],
) -> None:
    """Lê o PDF salvo em disco por `run_automation_for_cota` e grava uma cópia no Postgres."""
    try:
        with open(pdf_path, "rb") as f:
            content = f.read()
    except OSError as e:
        logger.error(f"[AUTOMAÇÃO] Não foi possível ler o PDF em '{pdf_path}' para salvar no banco: {e}")
        return

    try:
        db = SessionLocal()
        record = PdfDocument(
            automation_history_id=history_id,
            consultant_name=consultant_name,
            quota=quota,
            file_name=os.path.basename(pdf_path),
            content_type="application/pdf",
            size_bytes=len(content),
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()

        # Mantém no AutomationHistory uma referência de conveniência ao último PDF gerado.
        if history_id:
            hist = db.query(AutomationHistory).filter(AutomationHistory.id == history_id).first()
            if hist:
                hist.pdf_filename = os.path.basename(pdf_path)
                hist.pdf_path = pdf_path
                db.commit()
        db.close()
        logger.info(f"[AUTOMAÇÃO] PDF '{os.path.basename(pdf_path)}' salvo no banco de dados.")
    except Exception as e:
        logger.error(f"[AUTOMAÇÃO] Erro ao salvar PDF no banco de dados: {e}", exc_info=True)


def _run_browser_automation(config: AutomationConfigSchema, history_id: Optional[int] = None):
    global _current_driver, _current_progress, _current_final_status
    final_status = "finished"
    try:
        logger.info(f"[AUTOMAÇÃO] Criando e abrindo o Firefox para o consultor: {config.consultantName}")
        _current_driver = create_browser()

        # Efetua login no site do Servopa
        logger.info("[AUTOMAÇÃO] Efetuando login no portal Servopa...")
        login(_current_driver)
        logger.info("[AUTOMAÇÃO] Login concluído com sucesso. Navegador visível na tela!")

        # Processa cada cota recebida
        if config.bids:
            for idx, bid in enumerate(config.bids):
                if _current_driver is None:
                    logger.info("[AUTOMAÇÃO] Execução interrompida pelo usuário.")
                    final_status = "idle"
                    break

                cota_info = _parse_cota_item(bid)
                if not cota_info:
                    logger.warning(f"[AUTOMAÇÃO] Cota ignorada (formato inválido): {bid}")
                    if idx < len(_current_progress):
                        _current_progress[idx]["status"] = "invalido"
                        _current_progress[idx]["message"] = "Formato de cota inválido"
                    continue

                if idx < len(_current_progress):
                    _current_progress[idx]["status"] = "processando"

                logger.info(f"[AUTOMAÇÃO] Processando cota: {cota_info['original']}")
                status, msg, pdf_path = run_automation_for_cota(
                    _current_driver, cota_info, config.consultantName
                )
                logger.info(f"[AUTOMAÇÃO] Resultado da cota {cota_info['original']}: {status} - {msg}")

                if status == "SUCESSO" and pdf_path:
                    _save_pdf_to_db(config.consultantName, cota_info["original"], pdf_path, history_id)

                if idx < len(_current_progress):
                    _current_progress[idx]["status"] = status
                    _current_progress[idx]["message"] = msg

    except Exception as e:
        logger.error(f"[AUTOMAÇÃO ERRO] Falha durante a execução da automação: {e}", exc_info=True)
        final_status = "error"
        if _current_driver is None:
            logger.error("[AUTOMAÇÃO ERRO] O navegador não pôde ser iniciado.")
    finally:
        # Fecha o navegador automaticamente ao final da execução (sucesso ou erro).
        # Se o usuário já tiver chamado /stop manualmente, _current_driver já é None
        # nesse ponto e nada acontece aqui.
        if _current_driver is not None:
            try:
                _current_driver.quit()
            except Exception:
                pass
            _current_driver = None

        # Registra o resultado real desta execução para /status e /live poderem
        # informar corretamente "terminou certo" vs "terminou com erro" — sem isso
        # o frontend não tem como distinguir um crash de uma conclusão normal.
        _current_final_status = final_status

        erros_para_log = [
            {"cota": item.get("quota"), "status": item.get("status"), "mensagem": item.get("message")}
            for item in _current_progress
            if item.get("status") in ("ERRO_BENIGNO", "ERRO_CRITICO", "invalido")
        ]
        if erros_para_log:
            salvar_log_erros(config.consultantName, erros_para_log)

        if history_id:
            try:
                db = SessionLocal()
                rec = db.query(AutomationHistory).filter(AutomationHistory.id == history_id).first()
                if rec:
                    rec.status = final_status
                    db.commit()
                db.close()
            except Exception as ex:
                logger.error(f"Erro ao atualizar status do histórico {history_id}: {ex}")


@router.post("/start")
def start_automation(
    config: AutomationConfigSchema,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    global _current_history_id, _current_progress, _current_final_status
    print(f"[AUTOMAÇÃO] Solicitação recebida para o consultor: {config.consultantName}")

    # Reseta o resultado da execução anterior IMEDIATAMENTE (antes do navegador
    # sequer começar a abrir em background). Sem isso, /status e /live continuam
    # reportando o status final da execução passada ("finished"/"error"/"idle")
    # durante a janela em que _current_driver ainda é None — fazendo o frontend
    # achar que a automação já terminou assim que ela é iniciada.
    _current_final_status = "running"

    user_name = config.userName or config.consultantName
    user_email = config.userEmail or f"{user_name.lower().replace(' ', '.')}@servopa.com.br"

    quotas_list = []
    if config.bids:
        for bid in config.bids:
            c_info = _parse_cota_item(bid)
            if c_info:
                quotas_list.append(c_info["original"])
    quotas_summary = ", ".join(quotas_list)
    quotas_count = len(quotas_list)

    # Inicializa o checklist de progresso: uma entrada por cota recebida, na
    # mesma ordem/índice de config.bids (usado por _run_browser_automation e
    # transmitido pelo WebSocket /live para o painel).
    _current_progress = [
        {
            "quota": (_parse_cota_item(bid) or {}).get("original") or bid.quota or f"Cota {i + 1}",
            "status": "pendente",
            "message": None,
        }
        for i, bid in enumerate(config.bids or [])
    ]

    history_id = None
    try:
        db = SessionLocal()
        record = AutomationHistory(
            user_name=user_name,
            user_email=user_email,
            consultant_name=config.consultantName,
            quotas_summary=quotas_summary,
            quotas_count=quotas_count,
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        rec_id = getattr(record, "id", None)
        history_id = int(rec_id) if rec_id is not None else None
        _current_history_id = history_id
        db.close()
    except Exception as e:
        logger.error(f"[AUTOMAÇÃO] Erro ao gravar histórico no banco de dados: {e}")

    background_tasks.add_task(_run_browser_automation, config, history_id)
    return {
        "status": "running",
        "message": "Automação iniciada com sucesso. Abrindo o navegador Firefox...",
        "historyId": history_id,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/stop")
def stop_automation() -> Dict[str, Any]:
    global _current_driver, _current_history_id, _current_final_status
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

    _current_final_status = "idle"

    if _current_history_id:
        try:
            db = SessionLocal()
            rec = db.query(AutomationHistory).filter(AutomationHistory.id == _current_history_id).first()
            if rec:
                rec.status = "idle"
                db.commit()
            db.close()
        except Exception as ex:
            logger.error(f"Erro ao atualizar status do histórico {_current_history_id}: {ex}")

    return {
        "status": "idle",
        "message": "Automação encerrada e navegador fechado.",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


_STATUS_MESSAGES = {
    "running": "Automação em execução",
    "finished": "Automação concluída.",
    "error": "A automação foi interrompida por um erro antes de terminar.",
    "idle": "Aguardando início",
}


@router.get("/status")
def get_automation_status() -> Dict[str, Any]:
    status = "running" if _current_driver is not None else _current_final_status
    return {
        "status": status,
        "message": _STATUS_MESSAGES.get(status, _STATUS_MESSAGES["idle"]),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health")
def automation_health() -> Dict[str, Any]:
    """Verifica se o ambiente de automação (Firefox/GeckoDriver/diretórios) está pronto
    para uma execução, sem abrir nenhum navegador. Não expõe caminhos do sistema —
    apenas booleanos — então pode ser consultado livremente (ex.: monitoramento/deploy)."""
    checks = check_automation_environment()
    return {
        "ready": checks["ready"],
        "checks": {k: v for k, v in checks.items() if k != "ready"},
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history", response_model=List[HistoryOutSchema])
def list_history() -> List[HistoryOutSchema]:
    try:
        db = SessionLocal()
        records = db.query(AutomationHistory).order_by(AutomationHistory.created_at.desc()).all()
        result = []
        for r in records:
            result.append(
                HistoryOutSchema(
                    id=str(r.id),
                    executedBy={
                        "name": r.user_name,
                        "email": r.user_email,
                    },
                    consultantName=r.consultant_name,
                    quotasCount=r.quotas_count,
                    quotasSummary=r.quotas_summary or "",
                    createdAt=r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
                    status=r.status,
                    pdfFilename=r.pdf_filename,
                )
            )
        db.close()
        return result
    except Exception as e:
        logger.error(f"Erro ao buscar histórico do banco: {e}")
        return []


@router.delete("/history/{history_id}", status_code=204)
def delete_history(history_id: int) -> None:
    """Remove um registro específico do histórico de automações.

    Os PDFs associados (tabela `pdf_documents`) não são apagados — apenas
    perdem o vínculo com o histórico (FK com ON DELETE SET NULL), então
    continuam disponíveis na lista de PDFs gerados.
    """
    db = SessionLocal()
    try:
        record = db.query(AutomationHistory).filter(AutomationHistory.id == history_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Registro de histórico não encontrado.")
        db.delete(record)
        db.commit()
    finally:
        db.close()


@router.websocket("/live")
async def automation_live_view(websocket: WebSocket) -> None:
    """Transmite screenshots periódicas do navegador em execução para o frontend."""
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
                # Envia o resultado real da última execução ("idle"/"finished"/"error"),
                # não um "idle" genérico — é o que permite o frontend distinguir uma
                # conclusão normal de um crash antes de terminar de processar as cotas.
                await websocket.send_json({"type": "status", "status": _current_final_status})

            if _current_progress:
                await websocket.send_json({"type": "progress", "items": _current_progress})

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("[LIVE VIEW] Cliente desconectado.")

