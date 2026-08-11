"""
Módulo de automação Selenium para o Painel Servopa Consórcios.

Submodules:
  browser    — fábrica do WebDriver (create_browser)
  engine     — motor RPA: login, busca, lances, classificação de resultados
  locators   — seletores DOM centralizados (Page Object Pattern)
  pdf_parser — leitura de PDFs, extração de dados e renomeação padronizada
"""

from app.automation.browser import create_browser
from app.automation.engine import (
    get_driver,
    login,
    run_automation_for_cota,
    parse_lances_from_string,
    setup_logging,
    CaptchaDetectedException,
    InvalidCredentialsException,
)
from app.automation.pdf_parser import (
    extract_canonical_cota,
    parse_cota_from_filename,
    verificar_e_corrigir_nomes_pdf,
)

__all__ = [
    "create_browser",
    "get_driver",
    "login",
    "run_automation_for_cota",
    "parse_lances_from_string",
    "setup_logging",
    "CaptchaDetectedException",
    "InvalidCredentialsException",
    # pdf_parser
    "extract_canonical_cota",
    "parse_cota_from_filename",
    "verificar_e_corrigir_nomes_pdf",
]
