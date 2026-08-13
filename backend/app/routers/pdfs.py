"""Router de PDFs gerados pela automação.
=======================================
Os PDFs são persistidos diretamente no Postgres (tabela `pdf_documents`,
coluna `content` em bytea) por `_save_pdf_to_db` em `routers/automation.py`,
logo após `run_automation_for_cota` retornar sucesso. Este router lista e
serve o conteúdo binário a partir do banco — não depende mais do sistema de
arquivos, então os PDFs sobrevivem a reinícios/deploys que limpem o disco.
"""

import io
import zipfile
from collections import Counter
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.database import SessionLocal
from app.models.pdf_document import PdfDocument

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])


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
def download_all_pdfs() -> Response:
    """Empacota todos os PDFs salvos no banco num único .zip para download em massa."""
    db = SessionLocal()
    try:
        records = db.query(PdfDocument).order_by(PdfDocument.created_at.desc()).all()
        if not records:
            raise HTTPException(status_code=404, detail="Nenhum PDF encontrado para baixar.")

        buffer = io.BytesIO()
        nome_contagem: Counter[str] = Counter()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for r in records:
                nome = r.file_name or f"pdf-{r.id}.pdf"
                nome_contagem[nome] += 1
                # Evita sobrescrever arquivos com nomes repetidos dentro do zip
                if nome_contagem[nome] > 1:
                    base, _, ext = nome.rpartition(".")
                    nome = f"{base or nome} ({nome_contagem[nome]}).{ext or 'pdf'}"
                zip_file.writestr(nome, r.content)
        buffer.seek(0)

        zip_filename = f"pdfs-servopa-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.zip"
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
