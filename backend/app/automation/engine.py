"""
Motor principal da automação web — Servopa RPA
==============================================
Controla o Firefox via Selenium para interagir com o site do Consórcio Servopa
como um operador humano: faz login, busca cotas, preenche e registra lances,
baixa PDFs e classifica o resultado de cada cota.

Responsabilidades:
  - Configuração do WebDriver (get_driver)
  - Autenticação com CPF/CNPJ e senha (login)
  - Navegação até a tela de busca e preenchimento do grupo/cota/dígito
  - Lógica de oferta de lances livres e fixos
  - Funções de robustez: click_element, type_text_and_verify, remover_loading,
    aguardar_download_concluir, save_debug_artifacts, etc.
  - Parsing e classificação dos resultados (SUCESSO / ERRO_BENIGNO / ERRO_CRITICO)

Separação de responsabilidades:
  - locators/  : seletores DOM centralizados (Page Object Pattern)
  - browser.py : fábrica do WebDriver (create_browser) para a camada web/FastAPI
  - engine.py  : lógica de negócio (este arquivo)
"""

import os
import logging
import time
import shutil
import re
import hashlib
from datetime import datetime
from pathlib import Path
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.firefox.service import Service  # type: ignore
from selenium.webdriver.firefox.options import Options  # type: ignore
from selenium.common.exceptions import (  # type: ignore
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    InvalidSessionIdException,
    StaleElementReferenceException,
)
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore

from app.automation.locators import (
    ServopaLocators,
    ServopaGroupLocators,
    ServopaLanceLocators,
)

# ---------------------------------------------------------------------------
# Exceções customizadas
# ---------------------------------------------------------------------------


class CaptchaDetectedException(Exception):
    """Lançada quando um CAPTCHA é detectado na página."""


class InvalidCredentialsException(Exception):
    """Lançada quando o login falha por credenciais inválidas."""


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging():
    """Configura handlers separados de arquivo e console com formatação visual."""
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    general_handler = logging.FileHandler("automacao.log", mode="a", encoding="utf-8")
    general_handler.setLevel(logging.INFO)
    general_handler.setFormatter(file_formatter)

    erros_file = os.getenv("ERROS_FILE", "erros_lances.txt")
    error_handler = logging.FileHandler(erros_file, mode="a", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
    )

    logging.basicConfig(
        level=logging.INFO,
        handlers=[general_handler, error_handler, stream_handler],
        force=True,
    )


def flush_log_handlers():
    """Faz flush em todos os handlers do logger raiz, de forma segura."""
    try:
        for h in logging.getLogger().handlers or []:
            try:
                if hasattr(h, "flush"):
                    h.flush()
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Configuração a partir do .env
# ---------------------------------------------------------------------------

from dotenv import load_dotenv  # type: ignore

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(_BASE_DIR / ".env")
load_dotenv()


def _get_normalized_path(env_var: str):
    path = os.getenv(env_var)
    return os.path.normpath(path) if path else None


CPF_CNPJ = os.getenv("CPF_CNPJ", "")
SENHA = os.getenv("SENHA", "")
SERVOPA_URL = os.getenv("SERVOPA_URL", "https://www.consorcioservopa.com.br/vendas/login")
SERVOPA_LANCES_URL = os.getenv(
    "SERVOPA_LANCES_URL",
    "https://www.consorcioservopa.com.br/vendas/lances",
)
SERVOPA_BUSCAR_URL = os.getenv(
    "SERVOPA_BUSCAR_URL",
    "https://www.consorcioservopa.com.br/vendas/buscar",
)
ERROS_FILE = os.getenv("ERROS_FILE", "erros_lances.txt")
LANCE_LIVRE_PERCENTUAL = os.getenv("LANCE_LIVRE_PERCENTUAL", "40")
LANCE_LIVRE_DESCONTAR_CARTA = os.getenv("LANCE_LIVRE_DESCONTAR_CARTA", "30")
# Quanto tempo esperar o PDF aparecer/estabilizar na pasta de downloads antes
# de desistir (ERRO_CRITICO "Nenhum PDF apareceu na pasta de downloads.").
# Configurável porque em produção o container roda até MAX_CONCURRENT_AUTOMATIONS
# automações ao mesmo tempo disputando poucas vCPUs — sob essa carga o Firefox
# pode demorar bem mais que em desenvolvimento local (uma automação, máquina
# ociosa) pra gerar/baixar o PDF, mesmo quando tudo deu certo até aqui.
PDF_DOWNLOAD_TIMEOUT = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "180"))
GECKODRIVER_PATH = _get_normalized_path("GECKODRIVER_PATH")
FIREFOX_PROFILE_PATH = _get_normalized_path("FIREFOX_PROFILE_PATH")
DOWNLOAD_DIR = _get_normalized_path("DOWNLOAD_DIR")
FIREFOX_BINARY_PATH = _get_normalized_path("FIREFOX_BINARY_PATH")
# Pasta base para salvar PDFs: Lances/{consultor}/...
LANCES_BASE_DIR = os.getenv("LANCES_DIR") or "Lances"


# ---------------------------------------------------------------------------
# Inicialização do WebDriver
# ---------------------------------------------------------------------------


def get_driver(
    download_dir=None,
    display=None,
    firefox_profile_path=None,
    headless=None,
):
    """Configura e retorna uma instância do WebDriver do Firefox.

    Parâmetros opcionais para uso concorrente (multi-job):
    - download_dir: pasta de download exclusiva do job.
    - display: string tipo ':101' para display X virtual específico.
    - firefox_profile_path: sobrescreve o perfil do Firefox.
    - headless: força True/False; padrão calculado por contexto.
    """
    resolved_download_dir = download_dir or DOWNLOAD_DIR
    resolved_profile_path = (
        firefox_profile_path if firefox_profile_path is not None else FIREFOX_PROFILE_PATH
    )

    env_headless_str = os.getenv("HEADLESS")
    if env_headless_str is not None:
        default_headless = env_headless_str.lower() in ("true", "1", "yes")
    else:
        default_headless = display is None and not resolved_profile_path
    resolved_headless = headless if headless is not None else default_headless

    logging.info("Configurando instância do WebDriver...")
    if not all([GECKODRIVER_PATH, resolved_download_dir, FIREFOX_BINARY_PATH]):
        raise ValueError(
            "Variáveis de ambiente essenciais não definidas no .env: "
            "GECKODRIVER_PATH, DOWNLOAD_DIR, FIREFOX_BINARY_PATH"
        )

    # Garante que os caminhos críticos não são None após a validação acima
    assert resolved_download_dir is not None
    assert GECKODRIVER_PATH is not None
    assert FIREFOX_BINARY_PATH is not None

    os.makedirs(resolved_download_dir, exist_ok=True)

    options = Options()
    options.binary_location = FIREFOX_BINARY_PATH
    if resolved_profile_path:
        logging.info(f"Usando perfil do Firefox: {resolved_profile_path}")
        options.add_argument("-profile")
        options.add_argument(resolved_profile_path)
    if resolved_headless:
        options.add_argument("-headless")

    # Preferências de download automático de PDF
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", os.path.abspath(resolved_download_dir))
    options.set_preference("browser.download.useDownloadDir", True)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
    options.set_preference("pdfjs.disabled", True)
    options.set_preference("network.cookie.sameSite.laxByDefault", False)
    options.set_preference("network.cookie.sameSite.noneRequiresSecure", False)
    # Oculta navigator.webdriver para reduzir detecção de bot
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)

    service_env = None
    if display:
        logging.info(f"Direcionando WebDriver para o display virtual: {display}")
        service_env = {**os.environ, "DISPLAY": display}

    service = Service(GECKODRIVER_PATH, env=service_env)
    try:
        driver = webdriver.Firefox(service=service, options=options)
        logging.info("WebDriver do Firefox iniciado com sucesso.")
        return driver
    except WebDriverException as e:
        logging.error(f"Falha ao iniciar o WebDriver: {e}")
        raise


# ---------------------------------------------------------------------------
# Funções de apoio / robustez
# ---------------------------------------------------------------------------


def remover_loading(driver, total_timeout=3, interval=1):
    """Aguarda passivamente o overlay 'pace-active' desaparecer."""
    logging.info("Aguardando tela de loading ('pace-active') sumir...")
    try:
        WebDriverWait(driver, total_timeout).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, "pace-active"))
        )
        logging.info("Tela de loading sumiu normalmente.")
    except TimeoutException:
        logging.warning("Loading ainda presente após o limite; prosseguindo mesmo assim.")


def save_debug_artifacts(driver, base_dir, basename):
    """Salva screenshot (.png) e HTML (.html) para depuração."""
    try:
        os.makedirs(base_dir, exist_ok=True)
        png_path = os.path.join(base_dir, f"{basename}.png")
        html_path = os.path.join(base_dir, f"{basename}.html")
        try:
            driver.save_screenshot(png_path)
            logging.info(f"Screenshot salvo em: {png_path}")
        except Exception as e:
            logging.error(f"Não foi possível salvar screenshot: {e}")
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source or "")
            logging.info(f"HTML salvo em: {html_path}")
        except Exception as e:
            logging.error(f"Não foi possível salvar HTML: {e}")
    except Exception as e:
        logging.error(f"Falha ao preparar diretório de depuração: {e}")


def log_separator(char="-", width=60):
    logging.info(char * width)


def log_banner(title: str):
    line = "=" * max(40, len(title) + 10)
    logging.info(line)
    logging.info(f"  {title}")
    logging.info(line)


def _cookies_fingerprint(driver):
    """Retorna hash MD5 curto de cada cookie — não expõe o valor real no log."""
    try:
        cookies = driver.get_cookies()
        return {
            c.get("name"): hashlib.md5((c.get("value") or "").encode()).hexdigest()[:8]
            for c in cookies
        }
    except Exception as e:
        return {"__erro__": str(e)}


def _nav_snapshot(driver):
    """Captura url/title/navigationStart num único round-trip JS."""
    try:
        return driver.execute_script(
            "var n = performance.getEntriesByType('navigation')[0];"
            "return {url: document.location.href, title: document.title, "
            "navStart: performance.timing.navigationStart, "
            "navType: n ? n.type : null};"
        )
    except Exception as e:
        return {"__erro__": str(e)}


def check_for_captcha(driver):
    """Verifica proativamente por CAPTCHA e lança CaptchaDetectedException."""
    try:
        WebDriverWait(driver, 2).until(
            EC.visibility_of_element_located(ServopaLocators.CAPTCHA)
        )
        raise CaptchaDetectedException("CAPTCHA detectado na página.")
    except TimeoutException:
        pass


def _listar_pdfs_recursivo(download_path):
    """Varre `download_path` e subpastas em busca de arquivos .pdf concluídos.

    Necessário porque o site pode sugerir um nome de arquivo com um caminho
    embutido (ex: Content-Disposition contendo "Lances/arquivo.pdf"), o que
    faz o Firefox criar subpastas dentro da pasta de download configurada.
    Retorna caminhos RELATIVOS a `download_path` (podem incluir subpasta).
    """
    encontrados = []
    for raiz, _dirs, arquivos in os.walk(download_path):
        for nome in arquivos:
            if nome.endswith(".pdf") and not nome.endswith(".part"):
                caminho_absoluto = os.path.join(raiz, nome)
                encontrados.append(os.path.relpath(caminho_absoluto, download_path))
    return encontrados


def aguardar_download_concluir(download_path, timeout=PDF_DOWNLOAD_TIMEOUT):
    """Aguarda a conclusão do download de um PDF verificando estabilidade do tamanho.

    Busca recursivamente dentro de `download_path`. Retorna o caminho RELATIVO
    do arquivo (pode incluir subpasta) para uso com os.path.join(download_path, ...).
    """
    if not download_path:
        raise ValueError(
            "download_path vazio — DOWNLOAD_DIR não está configurado (.env) ou não "
            "foi propagado corretamente até esta função."
        )
    logging.info(f"Monitorando pasta de downloads (recursivo): {download_path}")
    start_time = time.time()
    time.sleep(2)
    while time.time() - start_time < timeout:
        arquivos = _listar_pdfs_recursivo(download_path)
        if arquivos:
            pdf_rel = arquivos[0]
            file_path = os.path.join(download_path, pdf_rel)
            logging.info(f"Arquivo '{pdf_rel}' encontrado. Verificando estabilidade...")
            last_size, stable_count = -1, 0
            while time.time() - start_time < timeout:
                try:
                    current_size = os.path.getsize(file_path)
                    if current_size == last_size and current_size > 0:
                        stable_count += 1
                        if stable_count >= 3:
                            logging.info(f"Download de '{pdf_rel}' concluído e estável.")
                            return pdf_rel
                    else:
                        stable_count = 0
                    last_size = current_size
                except FileNotFoundError:
                    time.sleep(1)
                    continue
                time.sleep(1)
            raise TimeoutException(f"Timeout aguardando estabilização de '{pdf_rel}'.")
        time.sleep(1)
    raise TimeoutException("Nenhum PDF apareceu na pasta de downloads.")


def aguardar_pdf_aparecer(download_path, timeout=4):
    """Verifica rapidamente (recursivo) se algum PDF apareceu na pasta.

    Retorna o caminho RELATIVO (pode incluir subpasta) ou None.
    """
    if not download_path:
        raise ValueError(
            "download_path vazio — DOWNLOAD_DIR não está configurado (.env) ou não "
            "foi propagado corretamente até esta função."
        )
    logging.info(f"Verificação rápida por PDF (até {timeout}s) em: {download_path}")
    start = time.time()
    while time.time() - start < timeout:
        arquivos = _listar_pdfs_recursivo(download_path)
        if arquivos:
            logging.info(f"PDF detectado rapidamente: {arquivos[0]}")
            return arquivos[0]
        time.sleep(0.3)
    return None


def sanitizar_nome_arquivo(nome: str) -> str:
    """Remove caracteres inválidos de um nome de arquivo."""
    return re.sub(r'[\\/:*?"<>|]', "_", nome)


def find_element(driver, by, value, timeout=3):
    """Aguarda o elemento ficar VISÍVEL e o retorna, ou None."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, value))
        )
    except TimeoutException:
        logging.warning(f"Elemento não ficou visível: {by}={value} em {timeout}s.")
        return None


def click_element(driver, by, value, timeout=3):
    """Clica em um elemento via JavaScript (robusto contra interceptações)."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        logging.error(f"Falha ao clicar em {value} via JavaScript: {e}")
        return False


def click_first_available(driver, locators, timeout_each=3):
    """Tenta clicar no primeiro seletor que funcionar dentre a lista fornecida."""
    for (by, value) in locators:
        logging.info(f"Tentando clicar: by={by}, value={value}")
        try:
            element = WebDriverWait(driver, timeout_each).until(
                EC.element_to_be_clickable((by, value))
            )
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            except Exception:
                pass
            try:
                driver.execute_script("arguments[0].click();", element)
                return True
            except Exception as e_js:
                logging.warning(f"Clique JS falhou para {value}: {e_js}")
                try:
                    element.click()
                    return True
                except Exception as e_native:
                    logging.warning(f"Clique nativo falhou para {value}: {e_native}")
        except TimeoutException:
            logging.info(f"Elemento não encontrado a tempo: {value}")
        except Exception as e:
            logging.warning(f"Erro ao preparar clique em {value}: {e}")
    logging.error("Nenhum seletor de clique funcionou.")
    return False


def find_first_present(driver, locators, timeout_each=3):
    """Retorna o primeiro elemento PRESENTE no DOM entre os locators, ou None."""
    for locator in locators:
        try:
            el = WebDriverWait(driver, timeout_each).until(
                EC.presence_of_element_located(locator)
            )
            return el
        except Exception:
            continue
    return None


def type_text_and_verify(driver, by, value, text, timeout=3, retries=3, delay=0.2, is_password=False):
    """Preenche um campo e verifica se o valor foi aplicado, com fallback JS.

    Para campos de senha (is_password=True), valida apenas que o comprimento > 0.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        except TimeoutException as e:
            last_error = e
            logging.warning(f"Campo não visível (tentativa {attempt}/{retries}): {by}={value}")
            continue

        try:
            try:
                element.clear()
            except Exception:
                pass
            try:
                element.click()
            except Exception:
                pass
            element.send_keys(text)
            time.sleep(delay)

            current = element.get_attribute("value") or ""
            if (is_password and len(current) > 0) or (
                not is_password and (str(text) in current or current in str(text))
            ):
                return True

            # Fallback via JavaScript com eventos nativos (React/Vue/Angular)
            driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
                "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                element,
                text,
            )
            time.sleep(delay)
            current = element.get_attribute("value") or ""
            if (is_password and len(current) > 0) or (
                not is_password and (str(text) in current or current in str(text))
            ):
                return True
        except Exception as e:
            last_error = e
            logging.warning(f"Falha ao digitar no campo (tentativa {attempt}/{retries}): {e}")

    logging.error(f"Não foi possível confirmar o preenchimento de {value}. Último erro: {last_error}")
    return False


def tratar_visualizador_pdf_se_necessario(driver, timeout=4):
    """Se o site, ao invés de baixar o comprovante sozinho, abriu o PDF no
    visualizador interno do Firefox (PDF.js) — seja em nova aba ou na mesma
    aba — detecta isso e clica no botão "Salvar" da barra de ferramentas
    (`downloadButton`) para forçar o download normal do navegador.

    Retorna True se um visualizador PDF.js foi detectado e tratado (indepen-
    dente do clique ter funcionado), False se nada foi detectado.
    """
    original_handle = driver.current_window_handle
    original_handles = set(driver.window_handles)

    def _viewer_presente(d):
        return find_element(d, *ServopaLanceLocators.PDF_VIEWER_TOOLBAR, timeout=1) is not None

    # Aguarda uma nova aba abrir OU o visualizador aparecer na aba atual
    nova_aba_handle = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        extras = [h for h in driver.window_handles if h not in original_handles]
        if extras:
            nova_aba_handle = extras[-1]
            break
        if _viewer_presente(driver):
            break
        time.sleep(0.2)

    tratou = False
    if nova_aba_handle:
        logging.info("[PDF VIEWER] Nova aba detectada; verificando se é o visualizador PDF.js...")
        driver.switch_to.window(nova_aba_handle)
        if _viewer_presente(driver):
            logging.info("[PDF VIEWER] Confirmado na nova aba. Clicando em 'Salvar'...")
            click_element(driver, *ServopaLanceLocators.PDF_VIEWER_DOWNLOAD_BUTTON, timeout=3)
            time.sleep(1)
            tratou = True
        try:
            driver.close()
        except Exception as e:
            logging.warning(f"[PDF VIEWER] Falha ao fechar aba extra: {e}")
        driver.switch_to.window(original_handle)
    elif _viewer_presente(driver):
        logging.info("[PDF VIEWER] Visualizador detectado na mesma aba. Clicando em 'Salvar'...")
        click_element(driver, *ServopaLanceLocators.PDF_VIEWER_DOWNLOAD_BUTTON, timeout=3)
        time.sleep(1)
        tratou = True
        try:
            driver.back()
            remover_loading(driver)
        except Exception as e:
            logging.warning(f"[PDF VIEWER] Falha ao voltar após o download: {e}")

    return tratou


# ---------------------------------------------------------------------------
# Lógica de negócio
# ---------------------------------------------------------------------------


def login(driver):
    """Realiza o login no sistema com verificações proativas de CAPTCHA e erro."""
    logging.info(f"Acessando URL de login: {SERVOPA_URL}")
    driver.get(SERVOPA_URL)
    remover_loading(driver)
    check_for_captcha(driver)
    logging.info("Nenhum CAPTCHA detectado. Preenchendo credenciais...")
    try:
        if not type_text_and_verify(driver, *ServopaLocators.USERNAME_FIELD, CPF_CNPJ):
            raise Exception("Falha ao preencher o campo CPF/CNPJ.")
        if not type_text_and_verify(driver, *ServopaLocators.PASSWORD_FIELD, SENHA, is_password=True):
            raise Exception("Falha ao preencher o campo Senha.")
        if not click_element(driver, *ServopaLocators.LOGIN_BUTTON):
            raise Exception("Falha ao clicar no botão de login.")

        logging.info(f"URL após tentativa de login: {driver.current_url}")

        login_error = find_element(driver, *ServopaLocators.LOGIN_ERROR_MESSAGE, timeout=3)
        if login_error:
            raise InvalidCredentialsException("Login falhou: CPF/CNPJ ou senha inválidos!")

        try:
            WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located(ServopaLocators.LOGOUT_BUTTON)
            )
            logging.info("Botão de Logout visível. Login bem-sucedido.")
        except TimeoutException:
            logging.warning("Botão de Logout NÃO visível após login. Possível falha ou redirecionamento inesperado.")

        logging.info("Login realizado com sucesso.")
        remover_loading(driver)
        return True
    except InvalidCredentialsException:
        raise
    except Exception as e:
        logging.error("Falha durante o login.")
        check_for_captcha(driver)
        raise e


def _navegar_e_buscar_cota(driver, cota_info):
    """Navega via menus até a busca e preenche grupo/cota/dígito."""
    from selenium.webdriver.common.keys import Keys  # type: ignore

    grupo = cota_info["grupo"]
    cota = cota_info["cota"]
    digito = cota_info["digito"]

    def _preencher_campos_busca() -> bool:
        """Tenta preencher grupo/cota/dígito na página atual. Retorna False (sem
        lançar exceção) se algum campo não aparecer — quem chama decide se tenta
        de novo ou desiste."""
        for loc, val in [
            (ServopaGroupLocators.GROUP_INPUT, grupo),
            (ServopaGroupLocators.COTA_INPUT, cota),
            (ServopaGroupLocators.DIGITO_INPUT, digito),
        ]:
            el = find_element(driver, *loc)
            if el is None:
                logging.warning(f"Campo de busca não encontrado: {loc}")
                return False
            driver.execute_script("arguments[0].value = '';", el)
            time.sleep(0.1)
            el.send_keys(val)
            time.sleep(0.3)
        return True

    if "vendas/buscar" not in driver.current_url:
        logging.info("Navegando para a tela de busca pelo menu...")
        if not click_element(driver, By.XPATH, "//a[contains(., 'Ferramentas Admin')]"):
            raise Exception("Falha ao clicar no menu 'Ferramentas Admin'")
        if not click_element(
            driver,
            By.XPATH,
            "//a[@href='https://www.consorcioservopa.com.br/vendas/buscar']",
        ):
            raise Exception("Falha ao clicar no submenu 'Buscar'")
    else:
        logging.info("Já estamos na página de busca; reaproveitando.")

    remover_loading(driver)

    logging.info(f"Preenchendo busca — Grupo: {grupo}, Cota: {cota}, Dígito: {digito}")
    time.sleep(0.3)

    if not _preencher_campos_busca():
        # O clique de menu "sucede" (dispara via JS) mesmo que a navegação real
        # não tenha completado — ex.: se a cota anterior deixou o driver num
        # estado ruim (aba extra, overlay preso) sob lentidão do container.
        # Sem essa recuperação, TODA cota seguinte falhava do mesmo jeito, em
        # cascata, porque nunca se tentava sair desse estado. Força uma
        # navegação de verdade (GET direto na URL, não clique de menu/SPA) e
        # tenta preencher de novo, uma vez, antes de desistir.
        logging.warning(
            "Campos de busca não apareceram após reaproveitar/clicar no menu — "
            "forçando navegação direta pra tela de busca e tentando de novo."
        )
        driver.get(SERVOPA_BUSCAR_URL)
        remover_loading(driver)
        time.sleep(0.5)
        if not _preencher_campos_busca():
            raise Exception("Campo de busca não encontrado mesmo após navegação direta.")

    debug_nav_dir = os.path.join(LANCES_BASE_DIR, "_DEBUG_NAV")
    cota_tag = (
        str(cota_info.get("original", f"{grupo}-{cota}-{digito}"))
        .replace(",", "-")
        .replace("/", "-")
    )

    # LOG: lê DOM antes do clique
    try:
        pre_click_vals = driver.execute_script(
            "return {"
            "grupo: document.getElementById('grupo') ? document.getElementById('grupo').value : null,"
            "plano: document.getElementById('plano') ? document.getElementById('plano').value : null,"
            "digito: document.getElementById('digito') ? document.getElementById('digito').value : null,"
            "navigatorWebdriver: navigator.webdriver"
            "};"
        )
        logging.info(f"[PRE-CLIQUE] DOM={pre_click_vals}")
    except Exception as e:
        logging.warning(f"[PRE-CLIQUE] Falha ao ler via JS: {e}")

    snap_antes = _nav_snapshot(driver)
    nav_start_antes = snap_antes.get("navStart") if isinstance(snap_antes, dict) else None
    logging.info(f"[PRE-CLIQUE] snapshot={snap_antes}")

    btn = find_element(driver, *ServopaGroupLocators.SEARCH_GROUP_BUTTON)
    if btn is None:
        raise Exception("Botão de busca não encontrado na página.")

    def _submit_ja_disparado() -> bool:
        try:
            return (btn.get_attribute("disabled") is not None) or (  # type: ignore[union-attr]
                "carregando" in (btn.text or "").lower()  # type: ignore[union-attr]
            )
        except StaleElementReferenceException:
            return True
        except Exception:
            return False

    clique_secundario = False
    try:
        btn.click()
        logging.info("[CLIQUE] btn.click() nativo retornou sem exceção.")
    except Exception as e:
        if _submit_ja_disparado():
            logging.info(f"[CLIQUE] Exceção ({e}), mas formulário já submetido. Ignorando.")
        else:
            logging.warning(f"[CLIQUE] Clique nativo falhou ({e}). Tentando via JS...")
            driver.execute_script("arguments[0].click();", btn)
            clique_secundario = True
    logging.info(f"[CLIQUE] clique_secundario={clique_secundario}")

    # Detecta navegações extras (diagnóstico de "pisca duplo").
    # Sai assim que a URL/título estabilizar por `estavel_min`, em vez de
    # bloquear sempre pelo tempo máximo — reduz bastante a espera no caso comum.
    navegacoes = []
    valor_anterior = nav_start_antes
    idx_nav = 0
    estavel_min = 0.4
    tempo_max = 2.5
    inicio = time.time()
    ultima_mudanca = inicio
    while time.time() - inicio < tempo_max:
        snap = _nav_snapshot(driver)
        nav_atual = snap.get("navStart") if isinstance(snap, dict) else None
        if nav_atual is not None and nav_atual != valor_anterior:
            idx_nav += 1
            evento = {"t": round(time.time(), 3), "snapshot": snap}
            navegacoes.append(evento)
            logging.warning(f"[NAVEGAÇÃO] #{idx_nav} detectada -> {evento}")
            try:
                save_debug_artifacts(driver, debug_nav_dir, f"NAV{idx_nav}-{cota_tag}")
            except Exception as e_dbg:
                logging.warning(f"[NAVEGAÇÃO] Erro ao salvar artefato: {e_dbg}")
            valor_anterior = nav_atual
            ultima_mudanca = time.time()
        elif time.time() - ultima_mudanca >= estavel_min:
            break
        time.sleep(0.15)

    if len(navegacoes) >= 2:
        logging.warning(f"[NAVEGAÇÃO] {len(navegacoes)} navegações distintas detectadas (esperado: 1).")
    else:
        logging.info(f"[NAVEGAÇÃO] {len(navegacoes)} navegação(ões) detectada(s) após clique (normal).")

    remover_loading(driver, total_timeout=3)
    logging.info("[PÓS-BUSCA] snapshot={0}".format(_nav_snapshot(driver)))

    try:
        error_msg = find_element(driver, By.CLASS_NAME, "error", timeout=2)
        if error_msg and "NAO EXISTEM COTAS" in error_msg.text:
            logging.warning("Site retornou 'Não existem cotas' após a busca.")
    except Exception:
        pass

    logging.info("Busca concluída.")
    return True


def run_automation_for_cota(driver, cota_info, consultor, download_dir=None):
    """Orquestra o fluxo completo para uma única cota.

    Retorna: (status, mensagem, caminho_pdf)
    status ∈ {'SUCESSO', 'ERRO_BENIGNO', 'ERRO_CRITICO'}
    caminho_pdf é o caminho absoluto do PDF salvo em disco quando status == 'SUCESSO',
    ou None nos demais casos.
    """
    download_dir = download_dir or DOWNLOAD_DIR
    grupo = cota_info["grupo"]
    cota = cota_info["cota"]
    digito = cota_info["digito"]
    log_banner(f"COTA {grupo}.{cota}-{digito}")

    try:
        # Defensivo: fecha abas extras deixadas por uma tentativa anterior que
        # falhou no meio do fluxo (ex.: a aba do visualizador de PDF que abre
        # ao registrar o lance, se algo interrompeu o fechamento normal dela).
        # Sem isso, o driver podia ficar preso numa aba errada e todas as
        # cotas seguintes falhavam em cascata por não achar nenhum elemento.
        if len(driver.window_handles) > 1:
            principal = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                try:
                    driver.switch_to.window(handle)
                    driver.close()
                except Exception as e:
                    logging.warning(f"Falha ao fechar aba extra órfã: {e}")
            driver.switch_to.window(principal)

        _navegar_e_buscar_cota(driver, cota_info)

        logging.info("Procurando tabela de resultados...")
        result_body = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.XPATH, "//tbody"))
        )
        all_rows = result_body.find_elements(By.XPATH, ".//tr")
        logging.info(f"Total de linhas no tbody: {len(all_rows)}")

        rows = [r for r in all_rows if len(r.find_elements(By.TAG_NAME, "td")) >= 7]
        logging.info(f"{len(rows)} linha(s) válida(s) (>= 7 colunas).")

        if not rows:
            save_debug_artifacts(
                driver,
                os.path.join(LANCES_BASE_DIR, consultor, "Erros"),
                f"DEBUG-ZERO-ROWS-{cota_info['original'].replace(',', '-')}",
            )
            return "ERRO_BENIGNO", "Cota não encontrada na busca.", None

        cota_ativa = False
        for i, row in enumerate(rows):
            cells = row.find_elements(By.TAG_NAME, "td")
            status_text = cells[-1].text.strip().upper()
            if status_text != "ATIVO" and len(cells) >= 8:
                status_text = cells[7].text.strip().upper()
            logging.info(f"Linha {i+1} — status: '{status_text}'")
            if status_text == "ATIVO":
                logging.info("Cota ATIVA encontrada. Clicando na linha...")
                try:
                    driver.execute_script("arguments[0].click();", row)
                    time.sleep(0.5)
                    children = row.find_elements(By.XPATH, ".//*[self::a or self::button]")
                    if children:
                        driver.execute_script("arguments[0].click();", children[0])
                except Exception as e:
                    logging.warning(f"Erro ao clicar na linha: {e}")
                cota_ativa = True
                break

        if not cota_ativa:
            return "ERRO_BENIGNO", "Nenhuma cota com status 'ATIVO' encontrada.", None

        remover_loading(driver)
        logging.info("Abrindo página de lances pela URL...")
        try:
            driver.get(SERVOPA_LANCES_URL)
        except WebDriverException as nav_e:
            logging.error(f"Falha ao navegar para página de lances: {nav_e}")
            return "ERRO_CRITICO", f"Navegação falhou: {nav_e}", None

        check_for_captcha(driver)

        logging.info("Aguardando estado estável da página de lances...")
        try:
            WebDriverWait(driver, 6).until(
                lambda d: find_element(d, By.CLASS_NAME, "tab-switcher", timeout=1)
                or find_element(d, *ServopaLanceLocators.LANCE_ERROR_BLOCK, timeout=1)
            )
            remover_loading(driver, total_timeout=2)

            error_block = find_element(
                driver, *ServopaLanceLocators.LANCE_ERROR_BLOCK, timeout=0.5
            )
            if error_block:
                error_text = (error_block.text or "").replace("Erro", "").strip()
                logging.info(f"Erro de negócio na página de lances: '{error_text}'")
                if "contemplada" in error_text.lower():
                    return "ERRO_BENIGNO", "Cota já está contemplada.", None
                if "cancelado" in error_text.lower():
                    return "ERRO_BENIGNO", "Extrato da cota está cancelado.", None
                return "ERRO_BENIGNO", f"Erro na página de lances: {error_text}", None

            logging.info("Página de lances carregada com sucesso.")
        except TimeoutException:
            logging.error("Página de lances não apresentou estado reconhecível.")
            save_debug_artifacts(
                driver,
                os.path.join(LANCES_BASE_DIR, consultor, "Erros"),
                f"ERRO-{cota_info['original'].replace(',', '-')}-lances-load",
            )
            return "ERRO_CRITICO", "Página de lances não carregou corretamente.", None

        if find_element(driver, *ServopaLanceLocators.LANCE_FIDELIDADE_TAB, timeout=2):
            return "ERRO_BENIGNO", "A cota possui Lance Fidelidade e não pode ser processada.", None

        log_separator()
        logging.info("[TIPO] Determinando tipo de lance pelo TAB ativo...")
        tab_ativo = find_element(driver, *ServopaLanceLocators.LANCE_ACTIVE_TAB, timeout=3)
        tipo_tab = (
            (tab_ativo.text or tab_ativo.get_attribute("textContent") or "").strip().upper()
            if tab_ativo else ""
        )
        _data_lance_raw: str | None = tab_ativo.get_attribute("data-lance") if tab_ativo else None
        data_lance = _data_lance_raw.upper() if _data_lance_raw else ""
        is_livre = (data_lance == "L") or ("LIVRE" in tipo_tab)

        if is_livre:
            logging.info("[TIPO] TAB ativo: Lance Livre. Verificando pré-condições...")
            if find_element(
                driver, *ServopaLanceLocators.LANCE_EMBUTIDO_OPTIONS_CONTAINER, timeout=1.5
            ):
                return "ERRO_BENIGNO", "Escolher Ofertar Com ou Sem Embutido", None

            logging.info("Preenchendo percentual e descontar carta...")
            ok_percent = False
            for locator in [
                ServopaLanceLocators.LANCE_LIVRE_PERCENTUAL_INPUT,
                ServopaLanceLocators.LANCE_LIVRE_PERCENTUAL_INPUT_ALT,
            ]:
                el = find_element(driver, *locator, timeout=3)
                if el and type_text_and_verify(driver, *locator, LANCE_LIVRE_PERCENTUAL):
                    ok_percent = True
                    break
            if not ok_percent:
                save_debug_artifacts(
                    driver,
                    os.path.join(LANCES_BASE_DIR, consultor, "Erros"),
                    f"ERRO-{cota_info['original'].replace(',', '-')}-preencher-percentual",
                )
                return "ERRO_CRITICO", "Falha ao preencher o campo Percentual do Lance Livre.", None

            el_desc = find_element(
                driver, *ServopaLanceLocators.LANCE_LIVRE_DESCONTAR_INPUT, timeout=3
            )
            if not el_desc or not type_text_and_verify(
                driver, *ServopaLanceLocators.LANCE_LIVRE_DESCONTAR_INPUT, LANCE_LIVRE_DESCONTAR_CARTA
            ):
                save_debug_artifacts(
                    driver,
                    os.path.join(LANCES_BASE_DIR, consultor, "Erros"),
                    f"ERRO-{cota_info['original'].replace(',', '-')}-preencher-descontar",
                )
                return "ERRO_CRITICO", "Falha ao preencher o campo 'Descontar da Carta'.", None
        else:
            logging.info("[TIPO] TAB ativo: Lance Fixo. Sem campos adicionais.")

        log_separator()
        logging.info("[SIMULAÇÃO] Simulando lance...")
        simular_locators = [
            ServopaLanceLocators.SIMULAR_BUTTON,
            (By.XPATH, "//a[@id='btn_simular']"),
            (By.XPATH, "//a[contains(normalize-space(.), 'Simular Lance')]"),
        ]
        if not click_first_available(driver, simular_locators, timeout_each=5):
            save_debug_artifacts(
                driver,
                os.path.join(LANCES_BASE_DIR, consultor, "Erros"),
                f"ERRO-{cota_info['original'].replace(',', '-')}-simular",
            )
            raise Exception("Falha ao acionar 'Simular Lance'.")

        time.sleep(0.5)
        remover_loading(driver)
        try:
            WebDriverWait(driver, 5).until(
                lambda d: find_element(d, *ServopaLanceLocators.REGISTRAR_LINK, timeout=1)
                or find_element(d, *ServopaLanceLocators.REGISTRAR_BUTTON, timeout=1)
                or find_element(d, *ServopaLanceLocators.PROTOCOLO_ANTERIOR_INPUT, timeout=1)
            )
        except Exception:
            logging.info("Sinais de mudança pós-simulação não apareceram; prosseguindo.")

        if find_element(driver, *ServopaLanceLocators.PROTOCOLO_ANTERIOR_INPUT, timeout=3):
            return "ERRO_BENIGNO", "Lance já realizado (protocolo anterior encontrado).", None

        log_separator()
        logging.info("[REGISTRO] Registrando lance...")
        registrar_locators = [
            ServopaLanceLocators.REGISTRAR_BUTTON,
            ServopaLanceLocators.REGISTRAR_LINK,
            ServopaLanceLocators.REGISTRAR_ABSOLUTE,
        ]
        try:
            WebDriverWait(driver, 4).until(
                lambda d: any(
                    WebDriverWait(d, 1).until(EC.element_to_be_clickable(loc))
                    for loc in registrar_locators
                )
            )
        except Exception:
            logging.info("'Registrar' ainda não clicável; tentando mesmo assim.")

        if not click_first_available(driver, registrar_locators, timeout_each=4):
            save_debug_artifacts(
                driver,
                os.path.join(LANCES_BASE_DIR, consultor, "Erros"),
                f"ERRO-{cota_info['original'].replace(',', '-')}-registrar",
            )
            raise Exception("Falha ao acionar 'Registrar'.")

        quick_pdf = aguardar_pdf_aparecer(download_dir or "", timeout=3)

        if not quick_pdf:
            # Em vez de baixar sozinho, o site pode ter aberto o comprovante no
            # visualizador de PDF interno do Firefox. Detecta e clica em "Salvar".
            if tratar_visualizador_pdf_se_necessario(driver, timeout=4):
                quick_pdf = aguardar_pdf_aparecer(download_dir or "", timeout=5)

        if not quick_pdf:
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(ServopaLanceLocators.MODAL_CONTAINER)
                )
                modal_text_el = find_element(
                    driver, *ServopaLanceLocators.MODAL_TEXT, timeout=2
                )
                modal_text = (modal_text_el.text if modal_text_el else "").strip()
                logging.info(f"Modal após Registrar: {modal_text}")
                click_first_available(
                    driver,
                    [ServopaLanceLocators.MODAL_OK_BUTTON, ServopaLanceLocators.MODAL_OK_BUTTON_BY_TEXT],
                    timeout_each=2,
                )
                return "ERRO_BENIGNO", f"Bloqueio de assembleia / modal: {modal_text}", None
            except TimeoutException:
                pass

        pdf_filename = aguardar_download_concluir(download_dir or "")
        nome_cliente_el = find_element(driver, *ServopaLanceLocators.NOME_CLIENTE_TEXT)
        nome_cliente = (nome_cliente_el.text if nome_cliente_el else "Desconhecido").strip()
        nome_cliente_sanitizado = sanitizar_nome_arquivo(nome_cliente)
        novo_nome = f"LANCE- {nome_cliente_sanitizado} {grupo}.{cota}-{digito}.pdf"
        pasta_consultor = os.path.join(LANCES_BASE_DIR, consultor)
        os.makedirs(pasta_consultor, exist_ok=True)
        caminho_destino = os.path.join(pasta_consultor, novo_nome)
        shutil.move(os.path.join(download_dir or "", pdf_filename), caminho_destino)
        logging.info(f"[SUCESSO] PDF salvo: {caminho_destino}")
        return "SUCESSO", "Lance registrado e PDF salvo com sucesso.", caminho_destino

    except Exception as e:
        error_message = f"{type(e).__name__}: {e}"
        logging.error(
            f"[CRÍTICO] Erro no fluxo de {cota_info['original']}: {error_message}",
            exc_info=True,
        )
        save_debug_artifacts(
            driver,
            os.path.join(LANCES_BASE_DIR, consultor, "Erros"),
            f"ERRO-{cota_info['original'].replace(',', '-')}",
        )
        return "ERRO_CRITICO", error_message, None


# ---------------------------------------------------------------------------
# Log consolidado de erros (erros_lances.txt)
# ---------------------------------------------------------------------------


def _resolver_caminho_erros_file() -> str:
    caminho = Path(ERROS_FILE)
    if not caminho.is_absolute():
        # Raiz do monorepo (um nível acima de backend/), não a raiz do backend.
        caminho = (_BASE_DIR.parent / caminho).resolve()
    return str(caminho)


def salvar_log_erros(consultor: str, erros: list) -> None:
    """Registra, de forma organizada, os lances que deram erro numa execução.

    `erros` é uma lista de dicts: {"cota": str, "status": str, "mensagem": str|None}.
    Cada execução gera um bloco delimitado por linhas de "=", contendo o
    consultor, data/hora e todas as cotas com erro daquela execução.
    Não escreve nada se a lista estiver vazia (execução sem erros).
    """
    if not erros:
        return

    caminho = _resolver_caminho_erros_file()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    separador = "=" * 70

    linhas = [
        separador,
        f"Consultor: {consultor}",
        f"Data/Hora: {agora}",
        f"Total de cotas com erro: {len(erros)}",
        "-" * 70,
    ]
    for item in erros:
        linhas.append(f"Cota: {item.get('cota', '(desconhecida)')}")
        linhas.append(f"  Status : {item.get('status', '(desconhecido)')}")
        linhas.append(f"  Motivo : {item.get('mensagem') or '(sem detalhes)'}")
        linhas.append("")
    linhas.append(separador)
    linhas.append("")

    try:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
        logging.info(f"[LOG ERROS] {len(erros)} erro(s) registrado(s) em: {caminho}")
    except Exception as e:
        logging.error(f"[LOG ERROS] Falha ao gravar '{caminho}': {e}")


# ---------------------------------------------------------------------------
# Parsing de entrada e classificação de resultados
# ---------------------------------------------------------------------------


def parse_lances_from_string(cotas_input: str):
    """Converte string de cotas em lista de dicts canônicos.

    Retorna: (cotas_validas, linhas_invalidas, linhas_invalidas_indexadas)
    """
    cotas = []
    invalidas = []
    invalidas_idx = []
    for idx, raw in enumerate(cotas_input.split("\n"), start=1):
        linha = (raw or "").strip()
        if not linha:
            continue
        partes = [p.strip() for p in linha.split(",")]
        if len(partes) == 3 and all(partes):
            grupo, cota, digito = partes
            cotas.append({"grupo": grupo, "cota": cota, "digito": digito, "original": linha})
        else:
            invalidas.append(linha)
            invalidas_idx.append((idx, linha))
    if invalidas:
        logging.warning(f"Linhas ignoradas (formato inválido): {invalidas}")
    return cotas, invalidas, invalidas_idx


def _classificar_benigno(mensagem: str) -> str:
    m = mensagem or ""
    prefix = "Erro na página de lances: "
    if m.startswith(prefix):
        return m[len(prefix):].strip()
    ml = m.lower()
    if "cota não encontrada" in ml:
        return "Cota Não Existe"
    if "nenhuma cota com status" in ml or "não ativa" in ml:
        return "Cota Não Ativa"
    if "protocolo anterior" in ml:
        return "Requer Protocolo"
    if "fidelidade" in ml:
        return "Lance Fidelidade"
    if "extrato da cota está cancelado" in ml:
        return "Extrato Cancelado"
    if "bloqueio de assembleia" in ml or "modal após registrar" in ml:
        return "Bloqueio em Assembleia"
    return m if m else "Benigno"


def _classificar_critico(erro: str) -> str:
    if not erro:
        return "Erro Genérico"
    tipo = erro.split(":", 1)[0].strip()
    if "TimeoutException" in tipo:
        return "TimeoutException"
    if "StaleElementReferenceException" in tipo:
        return "StaleElementReferenceException"
    if "WebDriverException" in tipo:
        return "WebDriverException"
    if "Falha ao acionar" in erro or "clicar" in erro.lower():
        return "Erro de Clique"
    return tipo or "Erro Genérico"
