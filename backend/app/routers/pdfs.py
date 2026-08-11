"""
Router de PDFs gerados pela automação.
=======================================
Sem tabela no banco por enquanto: a lista é montada varrendo diretamente a
pasta `Lances/{consultor}/*.pdf` em disco (mesma pasta onde `engine.py` salva
os comprovantes de lance já renomeados). Simples e sempre reflete o estado
real do sistema de arquivos, ao custo de não guardar histórico de execuções
que não geraram PDF (erros, cotas puladas etc.).
"""

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.automation.engine import LANCES_BASE_DIR

router = APIRouter(prefix="/pdfs", tags=["pdfs"])

# Diretório base do backend (pai de 'app')
_BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Subpastas que não são consultores (usadas para artefatos de erro/depuração)
_IGNORED_DIRS = {"Erros", "Conflitos", "_DEBUG_NAV"}


def _lances_root() -> Path:
    root = Path(LANCES_BASE_DIR)
    if not root.is_absolute():
        root = (_BASE_DIR / root).resolve()
    return root


def _encode_id(rel_path: str) -> str:
    """Codifica o caminho relativo do PDF (dentro de Lances/) num id opaco e seguro para URL."""
    return base64.urlsafe_b64encode(rel_path.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_id(pdf_id: str) -> str:
    padding = "=" * (-len(pdf_id) % 4)
    return base64.urlsafe_b64decode((pdf_id + padding).encode("ascii")).decode("utf-8")


class GeneratedPdfOut(BaseModel):
    id: str
    fileName: str
    consultantName: str
    createdAt: str
    url: str


@router.get("", response_model=List[GeneratedPdfOut])
def list_pdfs() -> List[GeneratedPdfOut]:
    root = _lances_root()
    if not root.exists():
        return []

    results: List[GeneratedPdfOut] = []
    for consultor_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        if consultor_dir.name in _IGNORED_DIRS:
            continue
        for pdf_file in sorted(consultor_dir.glob("*.pdf")):
            rel_path = pdf_file.relative_to(root).as_posix()
            mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime, tz=timezone.utc)
            pdf_id = _encode_id(rel_path)
            results.append(
                GeneratedPdfOut(
                    id=pdf_id,
                    fileName=pdf_file.name,
                    consultantName=consultor_dir.name,
                    createdAt=mtime.isoformat(),
                    url=f"/pdfs/{pdf_id}/download",
                )
            )

    results.sort(key=lambda p: p.createdAt, reverse=True)
    return results


@router.get("/{pdf_id}/download")
def download_pdf(pdf_id: str) -> FileResponse:
    root = _lances_root().resolve()
    try:
        rel_path = _decode_id(pdf_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Identificador de PDF inválido.")

    file_path = (root / rel_path).resolve()

    # Proteção contra path traversal: o caminho final precisa estar dentro de `root`.
    if root not in file_path.parents and file_path != root:
        raise HTTPException(status_code=400, detail="Identificador de PDF inválido.")

    if not file_path.is_file() or file_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF não encontrado.")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name,
    )