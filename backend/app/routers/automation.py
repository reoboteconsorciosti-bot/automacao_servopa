import asyncio
import os
import threading
import uuid
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect
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

# Quantas automações podem rodar ao mesmo tempo neste servidor. Cada uma abre
# um Firefox headless real (CPU/RAM de verdade) — ajuste conforme a capacidade
# do servidor via variável de ambiente, sem precisar mexer em código.
MAX_CONCURRENT_AUTOMATIONS = int(os.getenv("MAX_CONCURRENT_AUTOMATIONS", "3"))

# _jobs: um dicionário por execução em andamento (ou recém-terminada), no lugar
# das antigas variáveis globais únicas (_current_driver etc.) — que só
# conseguiam representar UMA automação por vez. Cada job tem seu próprio
# driver, progresso, perfil de Firefox e pasta de download, isolados dos
# demais. _slots controla quais dos slots 1..MAX_CONCURRENT_AUTOMATIONS estão
# ocupados, para nunca deixar mais que o limite rodando ao mesmo tempo.
_jobs_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}
_slots: Dict[int, Optional[str]] = {i: None for i in range(1, MAX_CONCURRENT_AUTOMATIONS + 1)}


def _slot_profile_path(slot: int) -> Optional[str]:
    """Caminho de perfil do Firefox exclusivo deste slot (sessão/cookies isolados
    dos outros slots). Sufixo sobre FIREFOX_PROFILE_PATH; None se não configurado
    (create_browser cai no perfil isolado padrão nesse caso)."""
    base = os.getenv("FIREFOX_PROFILE_PATH", "").strip()
    return f"{base}-slot{slot}" if base else None


def _slot_download_dir(slot: int) -> Optional[str]:
    """Pasta de download exclusiva deste slot — evita que PDFs baixados por
    execuções simultâneas diferentes se misturem na mesma pasta."""
    base = os.getenv("DOWNLOAD_DIR", "").strip()
    return f"{base}-slot{slot}" if base else None


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


def _run_browser_automation(config: AutomationConfigSchema, job_id: str, history_id: Optional[int] = None) -> None:
    job = _jobs[job_id]
    slot = job["slot"]
    final_status = "finished"
    try:
        logger.info(
            f"[AUTOMAÇÃO][{job_id}] Criando e abrindo o Firefox (slot {slot}/{MAX_CONCURRENT_AUTOMATIONS}) "
            f"para o consultor: {config.consultantName}"
        )
        driver = create_browser(
            profile_path_override=_slot_profile_path(slot),
            download_dir_override=_slot_download_dir(slot),
        )
        job["driver"] = driver

        # Efetua login no site do Servopa
        logger.info(f"[AUTOMAÇÃO][{job_id}] Efetuando login no portal Servopa...")
        login(driver)
        logger.info(f"[AUTOMAÇÃO][{job_id}] Login concluído com sucesso. Navegador visível na tela!")

        # Processa cada cota recebida
        if config.bids:
            progress = job["progress"]
            for idx, bid in enumerate(config.bids):
                if job["driver"] is None:
                    logger.info(f"[AUTOMAÇÃO][{job_id}] Execução interrompida pelo usuário.")
                    final_status = "idle"
                    break

                cota_info = _parse_cota_item(bid)
                if not cota_info:
                    logger.warning(f"[AUTOMAÇÃO][{job_id}] Cota ignorada (formato inválido): {bid}")
                    if idx < len(progress):
                        progress[idx]["status"] = "invalido"
                        progress[idx]["message"] = "Formato de cota inválido"
                    continue

                if idx < len(progress):
                    progress[idx]["status"] = "processando"

                logger.info(f"[AUTOMAÇÃO][{job_id}] Processando cota: {cota_info['original']}")
                status, msg, pdf_path = run_automation_for_cota(
                    job["driver"],
                    cota_info,
                    config.consultantName,
                    download_dir=_slot_download_dir(slot),
                )
                logger.info(f"[AUTOMAÇÃO][{job_id}] Resultado da cota {cota_info['original']}: {status} - {msg}")

                if status == "SUCESSO" and pdf_path:
                    _save_pdf_to_db(config.consultantName, cota_info["original"], pdf_path, history_id)

                if idx < len(progress):
                    progress[idx]["status"] = status
                    progress[idx]["message"] = msg

    except Exception as e:
        logger.error(f"[AUTOMAÇÃO ERRO][{job_id}] Falha durante a execução da automação: {e}", exc_info=True)
        final_status = "error"
        if job.get("driver") is None:
            logger.error(f"[AUTOMAÇÃO ERRO][{job_id}] O navegador não pôde ser iniciado.")
    finally:
        # Fecha o navegador automaticamente ao final da execução (sucesso ou erro).
        # Se o usuário já tiver chamado /stop manualmente, job["driver"] já é None
        # nesse ponto e nada acontece aqui.
        driver = job.get("driver")
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        job["driver"] = None
        job["final_status"] = final_status

        # Libera o slot — só agora, com o navegador já fechado, é que uma nova
        # automação pode ocupar esse mesmo slot.
        with _jobs_lock:
            if _slots.get(slot) == job_id:
                _slots[slot] = None

        erros_para_log = [
            {"cota": item.get("quota"), "status": item.get("status"), "mensagem": item.get("message")}
            for item in job["progress"]
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
    print(f"[AUTOMAÇÃO] Solicitação recebida para o consultor: {config.consultantName}")

    # Checklist de progresso: uma entrada por cota recebida, na mesma
    # ordem/índice de config.bids (usado por _run_browser_automation e
    # transmitido pelo WebSocket /live para o painel).
    progress = [
        {
            "quota": (_parse_cota_item(bid) or {}).get("original") or bid.quota or f"Cota {i + 1}",
            "status": "pendente",
            "message": None,
        }
        for i, bid in enumerate(config.bids or [])
    ]

    # Reserva um slot livre (1..MAX_CONCURRENT_AUTOMATIONS) de forma síncrona e
    # atômica, ANTES da resposta HTTP voltar — fecha a mesma janela de corrida
    # que a versão anterior (execução única) já fechava, agora generalizada
    # para N slots: sem isso, duas chamadas a /start quase simultâneas
    # poderiam "ganhar" o mesmo slot e cruzar navegador/progresso entre elas.
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        slot = next((s for s, occupant in _slots.items() if occupant is None), None)
        if slot is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Todas as {MAX_CONCURRENT_AUTOMATIONS} automações simultâneas permitidas "
                    "neste servidor já estão em uso no momento. Aguarde uma terminar e tente de novo."
                ),
            )
        _slots[slot] = job_id
        _jobs[job_id] = {
            "driver": None,
            "progress": progress,
            "history_id": None,
            "final_status": "running",
            "consultant_name": config.consultantName,
            "slot": slot,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

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
        _jobs[job_id]["history_id"] = history_id
        db.close()
    except Exception as e:
        logger.error(f"[AUTOMAÇÃO] Erro ao gravar histórico no banco de dados: {e}")

    background_tasks.add_task(_run_browser_automation, config, job_id, history_id)
    return {
        "status": "running",
        "message": (
            f"Automação iniciada com sucesso (slot {slot} de {MAX_CONCURRENT_AUTOMATIONS}). "
            "Abrindo o navegador Firefox..."
        ),
        "jobId": job_id,
        "historyId": history_id,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/stop")
def stop_automation(job_id: str = Query(...)) -> Dict[str, Any]:
    print(f"[AUTOMAÇÃO] Solicitação recebida para fechar o navegador e parar a automação (job {job_id})...")
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada (pode já ter terminado).")

    # Nota: o slot NÃO é liberado aqui — só quit() é chamado no driver, o que
    # sinaliza para o loop da tarefa em background parar. Quem libera o slot é
    # o próprio finally de _run_browser_automation, quando ela de fato terminar
    # de desenrolar. Liberar aqui abriria uma janela pra um /start novo colidir
    # com a tarefa em background anterior, que ainda pode estar no meio de uma
    # chamada Selenium.
    driver = job.get("driver")
    if driver is not None:
        try:
            driver.quit()
            print(f"[AUTOMAÇÃO] Navegador Firefox do job {job_id} encerrado com sucesso.")
        except Exception as e:
            print(f"[AUTOMAÇÃO AVISO] Erro ao fechar o navegador do job {job_id}: {e}")
        finally:
            job["driver"] = None
    else:
        print(f"[AUTOMAÇÃO] Nenhum navegador ativo para o job {job_id}.")

    job["final_status"] = "idle"

    history_id = job.get("history_id")
    if history_id:
        try:
            db = SessionLocal()
            rec = db.query(AutomationHistory).filter(AutomationHistory.id == history_id).first()
            if rec:
                rec.status = "idle"
                db.commit()
            db.close()
        except Exception as ex:
            logger.error(f"Erro ao atualizar status do histórico {history_id}: {ex}")

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
def get_automation_status(job_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    job = _jobs.get(job_id) if job_id else None
    if job is None:
        status = "idle"
    else:
        status = "running" if job.get("driver") is not None else job.get("final_status", "idle")
    return {
        "status": status,
        "message": _STATUS_MESSAGES.get(status, _STATUS_MESSAGES["idle"]),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/jobs")
def list_active_jobs() -> Dict[str, Any]:
    """Lista as automações em execução agora — útil para acompanhar quantos
    'computadores'/slots estão ocupados sem precisar abrir cada um."""
    with _jobs_lock:
        active = [
            {
                "jobId": job_id,
                "consultantName": job["consultant_name"],
                "slot": job["slot"],
                "startedAt": job["created_at"],
            }
            for job_id, job in _jobs.items()
            if job.get("driver") is not None
        ]
    return {
        "maxConcurrentAutomations": MAX_CONCURRENT_AUTOMATIONS,
        "activeCount": len(active),
        "jobs": active,
    }


@router.get("/health")
def automation_health() -> Dict[str, Any]:
    """Verifica se o ambiente de automação (Firefox/GeckoDriver/diretórios) está pronto
    para uma execução, sem abrir nenhum navegador. Não expõe caminhos do sistema —
    só booleanos, um número e um timestamp de marcador de persistência — então
    pode ser consultado livremente (ex.: monitoramento/deploy)."""
    checks = check_automation_environment()
    return {
        "ready": checks["ready"],
        "maxConcurrentAutomations": MAX_CONCURRENT_AUTOMATIONS,
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
    """Transmite screenshots periódicas do navegador de UM job específico
    (identificado por ?job_id=... na URL do WebSocket) para o frontend."""
    job_id = websocket.query_params.get("job_id")
    await websocket.accept()
    logger.info(f"[LIVE VIEW] Cliente conectado (job_id={job_id}).")
    try:
        while True:
            job = _jobs.get(job_id) if job_id else None
            driver = job.get("driver") if job else None
            if driver is not None:
                try:
                    frame = await run_in_threadpool(driver.get_screenshot_as_base64)
                    await websocket.send_json({"type": "frame", "image": frame})
                except Exception as e:
                    logger.warning(f"[LIVE VIEW] Falha ao capturar tela (job {job_id}): {e}")
                    await websocket.send_json({"type": "status", "status": "unavailable"})
            else:
                # Envia o resultado real da última execução desse job
                # ("idle"/"finished"/"error"), não um "idle" genérico — é o
                # que permite o frontend distinguir uma conclusão normal de
                # um crash antes de terminar de processar as cotas.
                final_status = job.get("final_status", "idle") if job else "idle"
                await websocket.send_json({"type": "status", "status": final_status})

            if job and job.get("progress"):
                await websocket.send_json({"type": "progress", "items": job["progress"]})

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(f"[LIVE VIEW] Cliente desconectado (job_id={job_id}).")
