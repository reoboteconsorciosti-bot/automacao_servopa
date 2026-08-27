"""
Router de erros de lances (erros_lances.txt)
=============================================
Serve/gerencia o arquivo consolidado de erros gravado por
`engine.py::salvar_log_erros` durante as execuções da automação.

Antes, quem lia esse arquivo era uma rota própria do Next.js
(`frontend/app/api/erros-lances/route.ts`), lendo direto do disco do
container do FRONTEND. Isso só "funcionava" em desenvolvimento local porque
frontend e backend rodam na mesma máquina/disco ali. Em produção, frontend e
backend são containers Docker separados com filesystems isolados — só o
backend (que é quem realmente escreve o arquivo) tem acesso a ele. Por isso
esse router existe: expõe erros_lances.txt via API, do mesmo jeito que
histórico/PDFs já fazem.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/api/erros-lances", tags=["erros-lances"])

# Diretório base do backend (pai de 'app')
_BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _resolve_erros_file() -> Path:
    """Mesma resolução de caminho usada por engine.py::_resolver_caminho_erros_file —
    ambos precisam apontar pro mesmo arquivo. Caminho relativo (padrão local:
    "erros_lances.txt") resolve pra raiz do monorepo; em produção, defina
    ERROS_FILE como caminho absoluto dentro do volume persistente (ex.:
    /data/logs/erros_lances.txt) para sobreviver a redeploys."""
    caminho = Path(os.getenv("ERROS_FILE", "erros_lances.txt"))
    if not caminho.is_absolute():
        caminho = (_BASE_DIR.parent / caminho).resolve()
    return caminho


def _read_content() -> Optional[str]:
    try:
        return _resolve_erros_file().read_text(encoding="utf-8")
    except OSError:
        return None


def _parse_erros_lances(content: str) -> List[Dict[str, Any]]:
    """Cada execução com erro gera um bloco delimitado por linhas de '=':

    ======================================================================
    Consultor: Patricia
    Data/Hora: 12/08/2026 15:31:48
    Total de cotas com erro: 1
    ----------------------------------------------------------------------
    Cota: 1560,1546,3
      Status : ERRO_BENIGNO
      Motivo : A cota possui Lance Fidelidade e não pode ser processada.
    ======================================================================
    """
    blocos = [b.strip() for b in re.split(r"={5,}", content) if b.strip()]
    resultado: List[Dict[str, Any]] = []

    for bloco in blocos:
        consultant_match = re.search(r"Consultor:\s*(.+)", bloco)
        if not consultant_match:
            continue

        date_match = re.search(r"Data/Hora:\s*(.+)", bloco)
        total_match = re.search(r"Total de cotas com erro:\s*(\d+)", bloco)

        errors: List[Dict[str, str]] = []
        cota_regex = re.compile(r"Cota:\s*(.+?)\s*\n\s*Status\s*:\s*(.+?)\s*\n\s*Motivo\s*:\s*(.+)")
        for m in cota_regex.finditer(bloco):
            errors.append(
                {
                    "cota": m.group(1).strip(),
                    "status": m.group(2).strip(),
                    "motivo": m.group(3).strip(),
                }
            )

        resultado.append(
            {
                "consultant": consultant_match.group(1).strip(),
                "dateTime": date_match.group(1).strip() if date_match else "",
                "total": int(total_match.group(1)) if total_match else len(errors),
                "errors": errors,
            }
        )

    # Bloco mais recente primeiro (o arquivo é append-only, cresce do mais antigo pro mais novo).
    resultado.reverse()
    return resultado


@router.get("")
def list_erros_lances() -> Dict[str, Any]:
    content = _read_content()
    if content is None:
        return {"blocos": []}
    return {"blocos": _parse_erros_lances(content)}


@router.get("/download")
def download_erros_lances() -> Response:
    """Devolve o conteúdo bruto de erros_lances.txt, exatamente como está em
    disco (UTF-8), como download de arquivo — sem nenhum parsing/reformatação."""
    content = _read_content()
    if content is None:
        raise HTTPException(status_code=404, detail="Arquivo erros_lances.txt não encontrado.")
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="erros_lances.txt"'},
    )


@router.delete("")
def delete_erros_lances() -> Dict[str, bool]:
    """Apaga o arquivo erros_lances.txt (limpa todo o histórico de erros de
    uma vez). O arquivo é append-only — o backend recria sozinho na próxima
    execução que tiver erro, começando do zero."""
    caminho = _resolve_erros_file()
    try:
        caminho.unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Não foi possível excluir o arquivo: {e}")
    return {"ok": True}
