"""
pdf_parser.py — Processamento e organização de arquivos PDF
===========================================================
Responsável por ler PDFs de comprovantes de lance baixados pelo motor de
automação, extrair os dados do consorciado (nome, grupo, cota, dígito) e
renomear os arquivos de forma padronizada.

Funções públicas:
  extract_canonical_cota(text)         — extrai (grupo, cota, digito) de qualquer string
  parse_cota_from_filename(filename)   — extrai (grupo, cota, digito) do nome do arquivo
  verificar_e_corrigir_nomes_pdf(path) — escaneia pasta, renomeia e trata conflitos

Funções internas:
  _sanitize_nome(nome)    — limpa sufixos indesejados do nome do consorciado
  _extrair_info_pdf(path) — lê texto do PDF e extrai nome/grupo/cota/dígito
"""

import logging
import os
import re
import shutil

from pypdf import PdfReader  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilitários públicos
# ---------------------------------------------------------------------------


def extract_canonical_cota(text: str | None):
    """Extrai um conjunto canônico (grupo, cota, digito) de uma string de texto.

    Suporta dois formatos:
      A) Três números separados: grupo(4 dígitos), cota(1-4 dígitos), dígito(1 dígito)
      B) Dois números: primeiro com 5+ dígitos → split grupo(4)+cota(resto), segundo é dígito

    Retorna tupla (grupo, cota, digito) ou None se o formato não for reconhecido.
    """
    if not text:
        return None

    parts = re.findall(r"\d+", str(text))

    if len(parts) == 3:
        grupo, cota, digito = parts
        if len(grupo) == 4 and 1 <= len(cota) <= 4 and len(digito) == 1:
            return (grupo, cota, digito)
        return None

    if len(parts) == 2:
        inteiro, digito = parts
        if len(digito) == 1 and len(inteiro) >= 5:
            grupo = inteiro[:4]
            cota = inteiro[4:]
            if 1 <= len(cota) <= 4:
                return (grupo, cota, digito)
        return None

    return None


def parse_cota_from_filename(filename: str):
    """Extrai (grupo, cota, digito) de um nome de arquivo formatado.

    Suporta nomes como: ``LANCE- NOME DO CLIENTE 1532.69-5.pdf``
    Retorna tupla (grupo, cota, digito) ou None.
    """
    match = re.search(
        r"LANCE[- ]?.*?(\d{4})[.,\s]?([\d,]+)[-\s]?(\d)\.pdf",
        filename,
        re.IGNORECASE,
    )
    if match:
        return (match.group(1), match.group(2), match.group(3))
    return None


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------


def _sanitize_nome(nome: str) -> str:
    """Limpa sufixos e padrões indesejados do nome do consorciado.

    Remove:
    - Sufixos "ASSEMBLEIA N 1234.56-7" e o que vier após
    - Padrões de grupo/cota/dígito no final da string
    - Espaços duplicados
    """
    if not nome:
        return nome
    n = str(nome)
    # Remove qualquer sufixo "ASSEMBLEIA / ASSEMBLÉIA N ..." e o que vier após
    n = re.split(r"\bASSEMBL[EÉ]IA\b", n, flags=re.IGNORECASE)[0]
    # Remove padrões de grupo/cota/dígito no final (pode haver múltiplos aninhados)
    while True:
        antes = n
        n = re.sub(r"\s*\d{4}[.,\s]?[\d,]+[-\s]?\d\s*$", "", n)
        if n == antes:
            break
    return re.sub(r"\s+", " ", n).strip()


def _extrair_info_pdf(caminho_pdf: str):
    """Lê o texto de um PDF e extrai nome do consorciado, grupo, cota e dígito.

    Retorna: (nome, grupo, cota, digito, erro_msg)
    Em caso de sucesso, erro_msg é None.
    Em caso de falha, os quatro primeiros valores são None e erro_msg contém a descrição.
    """
    filename_only = os.path.basename(caminho_pdf)
    logger.info(f"---- Analisando PDF: {filename_only} ----")

    try:
        reader = PdfReader(caminho_pdf)
        if not reader.pages:
            logger.warning(f"PDF '{filename_only}' corrompido ou sem páginas.")
            return None, None, None, None, "PDF corrompido ou sem páginas"

        texto = "".join(page.extract_text() or "" for page in reader.pages)
        texto_limpo = re.sub(r"\s+", " ", texto).strip()

    except Exception as e:
        logger.error(f"Erro crítico ao ler PDF '{filename_only}': {e}", exc_info=True)
        return None, None, None, None, f"Erro crítico de leitura: {e}"

    # -- Extração do nome --
    nome: str | None = None
    padroes_nome = [
        # Com lookahead por label comum que encerra o nome
        r"Consorciado\s*[:\-]?\s*([A-Za-zÀ-ÿ0-9&.,'\-\s()]+?)"
        r"(?=\s+(?:Grupo|Cota|Extrato|Dados|CPF|CNPJ|\d{4}[.,]))",
        r"Cliente\s*[:\-]?\s*([A-Za-zÀ-ÿ0-9&.,'\-\s()]+?)"
        r"(?=\s+(?:Grupo|Cota|Extrato|Dados|CPF|CNPJ|\d{4}[.,]))",
        r"Nome\s*[:\-]?\s*([A-Za-zÀ-ÿ0-9&.,'\-\s()]+?)"
        r"(?=\s+(?:Grupo|Cota|Extrato|Dados|CPF|CNPJ|\d{4}[.,]))",
        # Fallbacks sem lookahead (sanitizamos depois)
        r"Consorciado\s*[:\-]?\s*([A-Za-zÀ-ÿ0-9&.,'\-\s()]{5,})",
        r"Cliente\s*[:\-]?\s*([A-Za-zÀ-ÿ0-9&.,'\-\s()]{5,})",
    ]
    for pat in padroes_nome:
        m = re.search(pat, texto_limpo, re.IGNORECASE)
        if m:
            candidato = (m.group(1) or "").strip().upper()
            # Corta em palavras-chave comuns caso o lookahead não tenha funcionado
            candidato = re.split(
                r"\b(Grupo|Cota|Extrato|Dados|CPF|CNPJ)\b",
                candidato,
                flags=re.IGNORECASE,
            )[0].strip()
            # Remove números de grupo/cota capturados junto
            candidato = re.sub(r"\s*\d{4}[.,\s]?[\d,]+[-\s]?\d.*$", "", candidato).strip()
            if candidato and len(candidato) >= 3:
                nome = candidato
                break

    # -- Extração de grupo/cota/dígito --
    grupo_extracted: str | None = None
    cota_extracted: str | None = None
    digito_extracted: str | None = None
    cota_pattern = r"(\d{4})[.,\s]?([\d,]+)[-\s]?(\d)"

    # 1) Prioridade: logo após o nome
    if nome:
        escaped = re.escape(nome)
        m2 = re.search(rf"{escaped}\s*{cota_pattern}", texto_limpo, re.IGNORECASE)
        if m2:
            grupo_extracted, cota_extracted, digito_extracted = m2.group(1), m2.group(2), m2.group(3)

    # 2) Após o label "Cota"
    if not grupo_extracted:
        m3 = re.search(rf"Cota\s*{cota_pattern}", texto_limpo, re.IGNORECASE)
        if m3:
            grupo_extracted, cota_extracted, digito_extracted = m3.group(1), m3.group(2), m3.group(3)

    # 3) Busca geral no texto
    if not grupo_extracted:
        m4 = re.search(cota_pattern, texto_limpo)
        if m4:
            grupo_extracted, cota_extracted, digito_extracted = m4.group(1), m4.group(2), m4.group(3)

    # Fallback para nome: início do texto até o padrão de cota
    if not nome:
        m_inicio = re.search(rf"^([A-Za-zÀ-ÿ0-9&.,'\-\s()]+?)\s+{cota_pattern}", texto_limpo)
        if m_inicio:
            candidato = m_inicio.group(1).strip().upper()
            palavras_ignorar = ["COMPROVANTE", "REGISTRO", "LANCE", "EXTRATO", "CONSORCIO", "SERVOPA"]
            if not any(w in candidato for w in palavras_ignorar):
                nome = candidato

    # Fallback para grupo/cota/dígito: nome do arquivo
    if not (grupo_extracted and cota_extracted and digito_extracted):
        cota_file = parse_cota_from_filename(filename_only)
        if cota_file:
            grupo_extracted, cota_extracted, digito_extracted = cota_file
            logger.info(
                f"  -> Cota extraída do nome do arquivo (fallback): "
                f"{grupo_extracted}.{cota_extracted}-{digito_extracted}"
            )

    # Fallback para nome: nome do arquivo (entre "LANCE-" e os números)
    if not nome:
        mfile = re.search(
            r"LANCE[- ]?(.*?)\s+\d{4}[.,\s]?[\d,]+[-\s]?\d\.pdf",
            filename_only,
            re.IGNORECASE,
        )
        if mfile:
            nome = (mfile.group(1) or "").strip().upper()

    if nome:
        nome = _sanitize_nome(nome)

    # -- Resultado final --
    if grupo_extracted and cota_extracted and digito_extracted:
        grupo_clean = "".join(c for c in grupo_extracted if c.isdigit())
        cota_clean = "".join(c for c in cota_extracted if c.isdigit())
        digito_clean = "".join(c for c in digito_extracted if c.isdigit())

        if nome:
            logger.info(
                f"  ✓ PDF lido: Nome='{nome}' | Grupo={grupo_clean} | "
                f"Cota={cota_clean} | Dígito={digito_clean}"
            )
        else:
            logger.warning(
                f"  ⚠ Nome NÃO encontrado | Grupo={grupo_clean} | "
                f"Cota={cota_clean} | Dígito={digito_clean}"
            )
        return nome, grupo_clean, cota_clean, digito_clean, None

    erro_msg = (
        f"  ✗ Extração incompleta: Nome={'OK' if nome else 'FALTA'} | "
        f"Grupo={'OK' if grupo_extracted else 'FALTA'} | "
        f"Cota={'OK' if cota_extracted else 'FALTA'} | "
        f"Dígito={'OK' if digito_extracted else 'FALTA'}"
    )
    logger.error(erro_msg)
    return None, None, None, None, erro_msg


# ---------------------------------------------------------------------------
# Função principal de varredura e correção
# ---------------------------------------------------------------------------


def verificar_e_corrigir_nomes_pdf(consultor_path: str) -> dict:
    """Escaneia uma pasta de consultor, renomeia PDFs e trata conflitos.

    Estratégia:
    - 1ª passada: lê cada PDF, extrai dados do CONTEÚDO (fonte da verdade) e
      calcula o nome correto.
    - 2ª passada: renomeia os arquivos. Se o destino já existir, move o
      arquivo original para uma subpasta "Conflitos" (quarentena).
    - 3ª passada: tenta resolver os arquivos em quarentena.

    Retorna um dicionário com contadores:
      total_scanned, renamed, correct, conflicts, errors
    """
    logger.info(f"--- Iniciando verificação de nomes em: {consultor_path} ---")
    report = {
        "total_scanned": 0,
        "renamed": 0,
        "correct": 0,
        "conflicts": 0,
        "errors": 0,
    }

    if not os.path.exists(consultor_path):
        logger.warning(f"Pasta do consultor '{consultor_path}' não existe.")
        return report

    conflitos_path = os.path.join(consultor_path, "Conflitos")
    arquivos_para_renomear: list[tuple[str, str]] = []

    # 1ª Passada: identificar arquivos a renomear
    pdf_files = [
        f
        for f in os.listdir(consultor_path)
        if f.lower().endswith(".pdf") and f.upper().startswith("LANCE")
    ]
    report["total_scanned"] = len(pdf_files)

    for filename in pdf_files:
        caminho_completo = os.path.join(consultor_path, filename)
        nome_pdf, grupo_pdf, cota_pdf, digito_pdf, erro = _extrair_info_pdf(caminho_completo)

        if erro:
            logger.warning(f"Erro ao ler '{filename}': {erro}")
            report["errors"] += 1
            continue

        if not (grupo_pdf and cota_pdf and digito_pdf):
            logger.error(
                f"Dados incompletos em '{filename}': "
                f"Grupo={grupo_pdf}, Cota={cota_pdf}, Dígito={digito_pdf}"
            )
            report["errors"] += 1
            continue

        # Determina o nome base: conteúdo do PDF tem prioridade
        if nome_pdf:
            base_nome = nome_pdf
            logger.info(f"  -> Nome do conteúdo do PDF: '{base_nome}'")
        else:
            m = re.search(r"LANCE[- ]?(.*?)\s+\d{4}", filename, re.IGNORECASE)
            if m:
                base_nome = m.group(1).strip().upper()
                logger.info(f"  -> Nome extraído do arquivo (fallback): '{base_nome}'")
            else:
                logger.error(f"Não foi possível extrair nome para '{filename}'")
                report["errors"] += 1
                continue

        base_nome = _sanitize_nome(base_nome)
        logger.info(f"  -> Nome após sanitização: '{base_nome}'")

        if not base_nome or len(base_nome) < 3:
            logger.error(f"Nome inválido após sanitização para '{filename}': '{base_nome}'")
            report["errors"] += 1
            continue

        nome_sanitizado = re.sub(r'[\/:*?"<>|]', "_", base_nome)
        novo_nome = f"LANCE- {nome_sanitizado} {grupo_pdf}.{cota_pdf}-{digito_pdf}.pdf"

        logger.info(f"  -> Atual: '{filename}' | Novo: '{novo_nome}'")

        if filename == novo_nome:
            logger.info("  -> ✓ Nome já está correto")
            report["correct"] += 1
        else:
            logger.info("  -> ✗ Precisa renomear")
            arquivos_para_renomear.append((caminho_completo, novo_nome))

    if not arquivos_para_renomear:
        logger.info("Nenhum arquivo precisa ser renomeado.")
        return report

    # 2ª Passada: renomear com tratamento de conflitos
    for caminho_antigo, novo_nome in arquivos_para_renomear:
        caminho_novo = os.path.join(consultor_path, novo_nome)
        try:
            if os.path.exists(caminho_novo):
                logger.warning(
                    f"CONFLITO: '{novo_nome}' já existe. "
                    f"Movendo original para quarentena."
                )
                os.makedirs(conflitos_path, exist_ok=True)
                shutil.move(
                    caminho_antigo,
                    os.path.join(conflitos_path, os.path.basename(caminho_antigo)),
                )
                report["conflicts"] += 1
            else:
                os.rename(caminho_antigo, caminho_novo)
                logger.info(
                    f"CORRIGIDO: '{os.path.basename(caminho_antigo)}' -> '{novo_nome}'"
                )
                report["renamed"] += 1
        except Exception as e:
            logger.error(f"FALHA ao renomear '{os.path.basename(caminho_antigo)}': {e}")
            report["errors"] += 1

    # 3ª Passada: resolver quarentena
    if os.path.exists(conflitos_path):
        logger.info("--- Tentando resolver arquivos em quarentena ---")
        for filename in os.listdir(conflitos_path):
            caminho_quarentena = os.path.join(conflitos_path, filename)
            nome_pdf, grupo_pdf, cota_pdf, digito_pdf, erro = _extrair_info_pdf(caminho_quarentena)

            if erro:
                logger.warning(f"Erro ao processar quarentena '{filename}': {erro}")
                continue

            # Nome preferencial: extrair do próprio nome do arquivo em quarentena
            m = re.search(
                r"LANCE[- ]?(.*?)\s+\d{4}[.,\s]?[\d,]+[-\s]?\d\.pdf",
                filename,
                re.IGNORECASE,
            )
            if m:
                base_nome = m.group(1).strip().upper()
            else:
                base_nome = nome_pdf or ""
            base_nome = _sanitize_nome(base_nome)

            nome_sanitizado = re.sub(r'[\/:*?"<>|]', "_", base_nome)
            novo_nome_final = (
                f"LANCE- {nome_sanitizado} {grupo_pdf}.{cota_pdf}-{digito_pdf}.pdf"
            )
            caminho_final = os.path.join(consultor_path, novo_nome_final)

            if not os.path.exists(caminho_final):
                shutil.move(caminho_quarentena, caminho_final)
                logger.info(f"RESOLVIDO: '{filename}' -> '{novo_nome_final}'")
                report["conflicts"] -= 1
                report["renamed"] += 1
            else:
                logger.error(
                    f"NÃO RESOLVIDO: conflito persiste para '{filename}'. "
                    f"Arquivo permanece em quarentena."
                )

        # Remove a pasta de conflitos se ficou vazia
        if os.path.exists(conflitos_path) and not os.listdir(conflitos_path):
            os.rmdir(conflitos_path)
            logger.info("Pasta de conflitos resolvida e removida.")

    logger.info("--- Verificação de nomes finalizada ---")
    return report
