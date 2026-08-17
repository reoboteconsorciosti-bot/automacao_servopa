"""Router de PDFs gerados pela automação.
=======================================
Os PDFs são persistidos diretamente no Postgres (tabela `pdf_documents`,
coluna `content` em bytea) por `_save_pdf_to_db` em `routers/automation.py`,
logo após `run_automation_for_cota` retornar sucesso. Este router lista e
serve o conteúdo binário a partir do banco — não depende mais do sistema de
arquivos, então os PDFs sobrevivem a reinícios/deploys que limpem o disco.
"""

import io
import os
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.automation.engine import LANCES_BASE_DIR, sanitizar_nome_arquivo
from app.database import SessionLocal
from app.models.pdf_document import PdfDocument

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])

# Diretório base do backend (pai de 'app') — mesmo padrão usado em browser.py/engine.py
_BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _lances_root() -> Path:
    """Resolve o caminho absoluto da pasta Lances/ (mesma usada por engine.py para
    salvar os PDFs durante a automação: Lances/{consultor}/arquivo.pdf)."""
    root = Path(LANCES_BASE_DIR)
    if not root.is_absolute():
        root = (_BASE_DIR / root).resolve()
    return root


class GeneratedPdfOut(BaseModel):
    id: str
    fileName: str
    consultantName: str
    createdAt: str
    url: str


@router.get("", response_model=List[GeneratedPdfOut])
def list_pdfs() -> List[GeneratedPdfOut]:
    db = SessionLocal()
    try:
        records = db.query(PdfDocument).order_by(PdfDocument.created_at.desc()).all()
        return [
            GeneratedPdfOut(
                id=str(r.id),
                fileName=r.file_name,
                consultantName=r.consultant_name,
                createdAt=r.created_at.astimezone(timezone.utc).isoformat() if r.created_at else "",
                url=f"/api/pdfs/{r.id}/download",
            )
            for r in records
        ]
    finally:
        db.close()


@router.get("/download-all")
def download_all_pdfs(consultant: Optional[str] = Query(None)) -> Response:
    """Empacota PDFs salvos no banco num único .zip, organizados em uma pasta por
    consultor dentro do zip (Murilo/arquivo.pdf, Lucas Roques/arquivo.pdf, ...).

    Se `consultant` for informado, filtra apenas os PDFs daquele consultor
    (usado pelo botão "Baixar ZIP" de cada grupo na tela de PDFs gerados).

    Também garante que o mesmo PDF exista em disco em Lances/{consultor}/arquivo.pdf
    (criando os diretórios com os.makedirs, se necessário) — mantendo a pasta Lances/
    como espelho organizado do que está salvo no banco, mesmo para PDFs que só
    existiam no Postgres (ex.: restaurados de outra máquina/deploy).
    """
    db = SessionLocal()
    try:
        query = db.query(PdfDocument)
        if consultant:
            query = query.filter(PdfDocument.consultant_name == consultant)
        records = query.order_by(PdfDocument.created_at.desc()).all()
        if not records:
            raise HTTPException(status_code=404, detail="Nenhum PDF encontrado para baixar.")

        lances_root = _lances_root()

        buffer = io.BytesIO()
        nome_contagem: Counter[tuple] = Counter()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for r in records:
                consultor_nome = sanitizar_nome_arquivo((r.consultant_name or "Sem consultor").strip())
                nome = r.file_name or f"pdf-{r.id}.pdf"

                # Evita sobrescrever arquivos com nomes repetidos dentro da mesma pasta de consultor
                chave = (consultor_nome, nome)
                nome_contagem[chave] += 1
                if nome_contagem[chave] > 1:
                    base, _, ext = nome.rpartition(".")
                    nome = f"{base or nome} ({nome_contagem[chave]}).{ext or 'pdf'}"

                # Garante Lances/{consultor}/ em disco e grava o PDF ali, se ainda não existir
                pasta_consultor = lances_root / consultor_nome
                os.makedirs(pasta_consultor, exist_ok=True)
                caminho_arquivo = pasta_consultor / nome
                if not caminho_arquivo.exists():
                    with open(caminho_arquivo, "wb") as f:
                        f.write(r.content)

                arcname = f"{consultor_nome}/{nome}"
                zip_file.writestr(arcname, r.content)
        buffer.seek(0)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        if consultant:
            slug = re.sub(r"[^\w\-]+", "-", consultant.strip()).strip("-") or "consultor"
            zip_filename = f"pdfs-{slug}-{timestamp}.zip"
        else:
            zip_filename = f"pdfs-servopa-{timestamp}.zip"

        return Response(
            content=buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"',
            },
        )
    finally:
        db.close()


@router.get("/{pdf_id}/download")
def download_pdf(pdf_id: str, download: bool = Query(False)) -> Response:
    if not pdf_id.isdigit():
        raise HTTPException(status_code=400, detail="Identificador de PDF inválido.")

    db = SessionLocal()
    try:
        record = db.query(PdfDocument).filter(PdfDocument.id == int(pdf_id)).first()
        if not record:
            raise HTTPException(status_code=404, detail="PDF não encontrado.")

        disposition = "attachment" if download else "inline"
        return Response(
            content=record.content,
            media_type=record.content_type or "application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{record.file_name}"',
            },
        )
    finally:
        db.close()


@router.delete("/{pdf_id}", status_code=204)
def delete_pdf(pdf_id: str) -> None:
    if not pdf_id.isdigit():
        raise HTTPException(status_code=400, detail="Identificador de PDF inválido.")

    db = SessionLocal()
    try:
        record = db.query(PdfDocument).filter(PdfDocument.id == int(pdf_id)).first()
        if not record:
            raise HTTPException(status_code=404, detail="PDF não encontrado.")
        db.delete(record)
        db.commit()
    finally:
        db.close()
