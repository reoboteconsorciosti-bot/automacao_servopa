import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import urllib3  # type: ignore
from dotenv import load_dotenv  # type: ignore
from selenium import webdriver  # type: ignore
from selenium.common.exceptions import WebDriverException  # type: ignore
from selenium.webdriver.firefox.service import Service  # type: ignore
from selenium.webdriver.firefox.options import Options as FirefoxOptions  # type: ignore

# Caminho base do backend (diretório pai de 'app')
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carrega as variáveis do arquivo .env no backend (em produção/Docker, variáveis
# já injetadas pelo ambiente — ex.: EasyPanel — têm prioridade e não são
# sobrescritas por load_dotenv, que só preenche o que ainda não está definido).
load_dotenv(BASE_DIR / ".env")
load_dotenv()


# Locais padrão do Firefox por sistema operacional, usados como fallback quando
# FIREFOX_BINARY_PATH não é definido no .env/ambiente. Em produção (Docker/Linux)
# o Dockerfile já define FIREFOX_BINARY_PATH explicitamente; esta lista serve como
# rede de segurança para dev local e outros ambientes Linux não containerizados.
DEFAULT_FIREFOX_PATHS = [
    # Windows
    Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Mozilla Firefox" / "firefox.exe",
    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Mozilla Firefox" / "firefox.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Mozilla Firefox" / "firefox.exe",
    # Linux (Debian/Ubuntu instalam como firefox-esr; algumas distros usam firefox)
    Path("/usr/bin/firefox-esr"),
    Path("/usr/bin/firefox"),
    Path("/usr/local/bin/firefox"),
]


def _aumentar_pool_http(driver: "webdriver.Firefox", maxsize: int = 10) -> None:
    """O Selenium 4.x usa por padrão um pool HTTP (urllib3) de UMA conexão
    entre o processo Python e o GeckoDriver local. Isso é suficiente enquanto
    só uma "linha de execução" fala com o driver por vez — mas a Visualização
    ao Vivo (WebSocket /live, que tira um screenshot por segundo do mesmo
    driver numa thread separada, rodando em paralelo com a automação
    principal) faz duas threads disputarem essa única conexão ao mesmo tempo.
    Resultado: "Connection pool is full, discarding connection" nos logs, e o
    urllib3 tem que abrir uma conexão TCP nova a cada comando em vez de
    reaproveitar — bem mais lento, e só acontece em produção porque só lá a
    Visualização ao Vivo fica aberta de verdade durante os testes (é o que
    explica o "funciona rápido em localhost, trava em produção").

    A API pública do Selenium 4.46 não expõe esse tamanho de pool direto no
    construtor do Firefox(), então ajusta depois de criado. Cercado de
    try/except porque mexe num atributo interno (`_conn`) que pode mudar em
    versões futuras — se falhar, a automação segue funcionando, só sem esse
    reforço de performance.
    """
    try:
        executor = driver.command_executor
        if getattr(executor, "_conn", None) is not None:
            executor._conn = urllib3.PoolManager(maxsize=maxsize)  # type: ignore[union-attr]
    except Exception as e:
        print(f"[AUTOMAÇÃO AVISO] Não foi possível aumentar o pool de conexões HTTP: {e}")


def create_browser(
    profile_path_override: Optional[str] = None,
    download_dir_override: Optional[str] = None,
) -> webdriver.Firefox:
    """
    Configura e inicializa a instância do WebDriver para Firefox com GeckoDriver.

    Parâmetros opcionais (usados para rodar várias automações ao mesmo tempo,
    cada uma com seu próprio perfil/pasta de download — sem eles, cai no
    comportamento de sempre, lendo FIREFOX_PROFILE_PATH/DOWNLOAD_DIR do .env):
    - profile_path_override: sobrescreve FIREFOX_PROFILE_PATH para esta chamada.
    - download_dir_override: sobrescreve DOWNLOAD_DIR para esta chamada.

    Variáveis de ambiente utilizadas (quando os parâmetros acima não são informados):
    - GECKODRIVER_PATH: caminho relativo ou absoluto para o geckodriver.exe
    - FIREFOX_BINARY_PATH: caminho opcional para o executável do Firefox
    - FIREFOX_PROFILE_PATH: caminho opcional para o perfil do Firefox
    - HEADLESS: "true" para ocultar a janela ou "false" (padrão) para exibir o navegador na tela
    """
    geckodriver_env = os.getenv("GECKODRIVER_PATH", "./drivers/geckodriver.exe").strip()
    firefox_binary_env = os.getenv("FIREFOX_BINARY_PATH", "").strip()
    firefox_profile_env = (
        profile_path_override if profile_path_override is not None else os.getenv("FIREFOX_PROFILE_PATH", "").strip()
    )
    download_dir_env = (
        download_dir_override if download_dir_override is not None else os.getenv("DOWNLOAD_DIR", "").strip()
    )
    headless_env = os.getenv("HEADLESS", "false").strip().lower() == "true"

    # Resolve o caminho do GeckoDriver
    geckodriver_path = Path(geckodriver_env)
    if not geckodriver_path.is_absolute():
        geckodriver_path = (BASE_DIR / geckodriver_path).resolve()

    # Resolve a pasta de downloads (onde o Firefox salva os PDFs dos lances)
    if not download_dir_env:
        raise ValueError(
            "DOWNLOAD_DIR não definido no .env. É necessário para o Firefox saber "
            "onde salvar os PDFs baixados durante a automação."
        )
    download_dir = Path(download_dir_env)
    if not download_dir.is_absolute():
        download_dir = (BASE_DIR / download_dir).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)

    def _apply_download_preferences(opts: FirefoxOptions) -> None:
        """Configura o Firefox para baixar PDFs automaticamente na pasta definida,
        sem abrir o visualizador interno nem perguntar onde salvar."""
        opts.set_preference("browser.download.folderList", 2)
        opts.set_preference("browser.download.dir", str(download_dir))
        opts.set_preference("browser.download.useDownloadDir", True)
        opts.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf")
        opts.set_preference("pdfjs.disabled", True)

    options = FirefoxOptions()
    _apply_download_preferences(options)

    # Configuração explícita de Headless (padrão: False / Visível)
    if headless_env:
        options.add_argument("--headless")
        # Sem isso, o Firefox headless abre com um viewport pequeno/inconsistente
        # (não existe janela real de desktop pra herdar o tamanho). Sob um
        # viewport pequeno, o CSS responsivo do site pode trocar de layout —
        # escondendo/reposicionando o botão "Registrar" real por trás de um
        # elemento que ainda existe no DOM (o clique via JS "funciona", não
        # lança exceção, mas não aciona nada) — sintoma batendo com o que só
        # acontece em produção (headless) e nunca em desenvolvimento (navegador
        # visível, tamanho de janela normal de desktop).
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")
        print("[AUTOMAÇÃO] Modo Headless ativado (viewport 1920x1080).")
    else:
        print("[AUTOMAÇÃO] Modo VISÍVEL ativado (Headless: False). O navegador abrirá na tela.")

    # Configura o binário do Firefox
    if firefox_binary_env:
        binary_path = Path(firefox_binary_env)
        if not binary_path.is_absolute():
            binary_path = (BASE_DIR / binary_path).resolve()
        options.binary_location = str(binary_path)
    else:
        # Se não configurado explicitamente no .env, busca nos caminhos padrão do sistema
        for default_path in DEFAULT_FIREFOX_PATHS:
            if default_path.exists():
                options.binary_location = str(default_path)
                break

    # Configura o perfil do Firefox com verificação de bloqueio
    use_profile = False
    if firefox_profile_env:
        profile_path = Path(firefox_profile_env)
        if not profile_path.is_absolute():
            profile_path = (BASE_DIR / profile_path).resolve()

        if not profile_path.exists():
            # Primeira execução com um volume persistente novo/vazio (ex.: /data/firefox-profile
            # recém-montado no EasyPanel): cria o diretório em vez de descartar a configuração —
            # o Firefox inicializa um perfil válido nele no primeiro uso.
            try:
                profile_path.mkdir(parents=True, exist_ok=True)
                print(f"[AUTOMAÇÃO] Diretório de perfil criado (primeira execução): {profile_path}")
            except OSError as e:
                print(f"[AUTOMAÇÃO AVISO] Não foi possível criar o diretório de perfil ({e}). Usando perfil isolado.")
                profile_path = None  # type: ignore[assignment]

        if profile_path is not None:
            # Verifica se o perfil está em uso (presença de parent.lock, criado pelo Firefox)
            lock_file = profile_path / "parent.lock"
            if lock_file.exists():
                print(
                    f"[AUTOMAÇÃO AVISO] O perfil '{profile_path.name}' está em uso pelo Firefox. "
                    "Para evitar recusa de conexão, abrindo em um perfil novo isolado."
                )
            elif not os.access(profile_path, os.W_OK):
                print(
                    f"[AUTOMAÇÃO AVISO] Sem permissão de escrita no perfil '{profile_path.name}'. "
                    "Abrindo em um perfil novo isolado."
                )
            else:
                options.profile = str(profile_path)
                use_profile = True

    # Checagens de pré-voo: falhar cedo com mensagem clara, em vez de deixar o
    # Selenium/GeckoDriver lançar um erro genérico difícil de diagnosticar.
    if not geckodriver_path.exists():
        raise RuntimeError(
            f"GeckoDriver não encontrado em '{geckodriver_path}'. Verifique a variável "
            "GECKODRIVER_PATH (em produção, o Dockerfile já define /usr/bin/geckodriver)."
        )
    if not options.binary_location:
        raise RuntimeError(
            "Executável do Firefox não encontrado. Defina FIREFOX_BINARY_PATH ou instale o "
            "Firefox em um dos caminhos padrão do sistema (em produção, o Dockerfile já "
            "define /usr/bin/firefox-esr)."
        )

    service = Service(executable_path=str(geckodriver_path))

    try:
        driver = webdriver.Firefox(service=service, options=options)
        _aumentar_pool_http(driver)
        return driver
    except WebDriverException as exc:
        # Se falhou usando perfil, tenta sem o perfil como fallback automático — cobre casos
        # como perfil corrompido ou incompatível que não foram detectados nas checagens acima.
        if use_profile:
            print("[AUTOMAÇÃO AVISO] Falha ao abrir com o perfil configurado. Tentando abrir perfil isolado...")
            fallback_options = FirefoxOptions()
            _apply_download_preferences(fallback_options)
            if headless_env:
                fallback_options.add_argument("--headless")
                fallback_options.add_argument("--width=1920")
                fallback_options.add_argument("--height=1080")
            if options.binary_location:
                fallback_options.binary_location = options.binary_location
            try:
                driver = webdriver.Firefox(service=service, options=fallback_options)
                _aumentar_pool_http(driver)
                return driver
            except WebDriverException as fallback_exc:
                raise RuntimeError(
                    f"Falha ao iniciar o WebDriver mesmo com perfil isolado: {fallback_exc}"
                ) from fallback_exc

        mensagem = str(exc).lower()
        if "permission denied" in mensagem:
            raise RuntimeError(f"Permissão negada ao iniciar o Firefox/GeckoDriver: {exc}") from exc
        if "timed out" in mensagem or "timeout" in mensagem:
            raise RuntimeError(f"Timeout ao iniciar o WebDriver (Firefox demorou demais para responder): {exc}") from exc
        if "unexpectedly closed" in mensagem or "process unexpectedly closed" in mensagem:
            raise RuntimeError(f"O Firefox encerrou inesperadamente ao iniciar: {exc}") from exc
        raise RuntimeError(f"Falha ao iniciar o WebDriver: {exc}") from exc


def check_automation_environment() -> dict:
    """Verifica os pré-requisitos da automação (Firefox, GeckoDriver, diretórios de
    perfil/download) sem abrir nenhum navegador — só inspeciona filesystem e env vars.

    Usado pelo endpoint de health-check (`GET /api/automation/health`). Retorna apenas
    booleanos: nunca inclua caminhos, variáveis de ambiente ou outros detalhes do
    sistema no retorno, pois este resultado pode ser exposto publicamente.
    """
    geckodriver_env = os.getenv("GECKODRIVER_PATH", "./drivers/geckodriver.exe").strip()
    firefox_binary_env = os.getenv("FIREFOX_BINARY_PATH", "").strip()
    firefox_profile_env = os.getenv("FIREFOX_PROFILE_PATH", "").strip()
    download_dir_env = os.getenv("DOWNLOAD_DIR", "").strip()

    geckodriver_path = Path(geckodriver_env)
    if not geckodriver_path.is_absolute():
        geckodriver_path = (BASE_DIR / geckodriver_path).resolve()
    geckodriver_ok = geckodriver_path.exists() and os.access(geckodriver_path, os.X_OK)

    firefox_binary_path = None
    if firefox_binary_env:
        binary_path = Path(firefox_binary_env)
        if not binary_path.is_absolute():
            binary_path = (BASE_DIR / binary_path).resolve()
        if binary_path.exists():
            firefox_binary_path = binary_path
    else:
        for default_path in DEFAULT_FIREFOX_PATHS:
            if default_path.exists():
                firefox_binary_path = default_path
                break
    firefox_ok = firefox_binary_path is not None

    profile_configured = bool(firefox_profile_env)
    profile_writable = True
    profile_path = None
    if firefox_profile_env:
        profile_path = Path(firefox_profile_env)
        if not profile_path.is_absolute():
            profile_path = (BASE_DIR / profile_path).resolve()
        target = profile_path if profile_path.exists() else profile_path.parent
        profile_writable = target.exists() and os.access(target, os.W_OK)

    download_dir_configured = bool(download_dir_env)
    download_dir_writable = False
    if download_dir_env:
        download_dir = Path(download_dir_env)
        if not download_dir.is_absolute():
            download_dir = (BASE_DIR / download_dir).resolve()
        try:
            download_dir.mkdir(parents=True, exist_ok=True)
            download_dir_writable = os.access(download_dir, os.W_OK)
        except OSError:
            download_dir_writable = False

    ready = (
        geckodriver_ok
        and firefox_ok
        and download_dir_configured
        and download_dir_writable
        and (profile_writable if profile_configured else True)
    )

    # Marcador de persistência real (não apenas "gravável agora"): na primeira
    # chamada, grava um timestamp num arquivo dentro do volume persistente. Se
    # o volume estiver montado de verdade (ex.: /data no EasyPanel), esse
    # timestamp permanece o MESMO entre deploys — se aparecer sempre próximo
    # do horário atual a cada chamada após um redeploy, o volume não está
    # persistindo, só existe na camada descartável do container.
    persistence_marker_since = None
    marker_root = profile_path.parent if profile_path is not None else None
    if marker_root is None and download_dir_env:
        marker_root = Path(download_dir_env)
        if not marker_root.is_absolute():
            marker_root = (BASE_DIR / marker_root).resolve()
        marker_root = marker_root.parent
    if marker_root is not None:
        try:
            marker_root.mkdir(parents=True, exist_ok=True)
            marker_path = marker_root / ".persistence-marker"
            if marker_path.exists():
                persistence_marker_since = marker_path.read_text().strip()
            else:
                persistence_marker_since = datetime.now(timezone.utc).isoformat()
                marker_path.write_text(persistence_marker_since)
        except OSError:
            persistence_marker_since = None

    return {
        "ready": ready,
        "geckodriverFound": geckodriver_ok,
        "firefoxFound": firefox_ok,
        "profileConfigured": profile_configured,
        "profileWritable": profile_writable,
        "downloadDirConfigured": download_dir_configured,
        "downloadDirWritable": download_dir_writable,
        "persistenceMarkerSince": persistence_marker_since,
    }


if __name__ == "__main__":
    print("=== Teste de Infraestrutura do Selenium + Firefox ===")
    driver = create_browser()
    try:
        url_teste = "https://www.google.com"
        print(f"Abrindo URL de teste: {url_teste}")
        driver.get(url_teste)
        print(f"Página carregada com sucesso! Título: {driver.title}")
        input("\nPressione Enter para fechar o navegador...")
    finally:
        driver.quit()
        print("Navegador encerrado com sucesso.")
