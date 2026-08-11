import os
from pathlib import Path
from dotenv import load_dotenv  # type: ignore
from selenium import webdriver  # type: ignore
from selenium.webdriver.firefox.service import Service  # type: ignore
from selenium.webdriver.firefox.options import Options as FirefoxOptions  # type: ignore

# Caminho base do backend (diretório pai de 'app')
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carrega as variáveis do arquivo .env no backend
load_dotenv(BASE_DIR / ".env")
load_dotenv()


# Locais padrão comuns do Firefox no Windows (usados se FIREFOX_BINARY_PATH não for especificado no .env)
DEFAULT_FIREFOX_PATHS = [
    Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Mozilla Firefox" / "firefox.exe",
    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Mozilla Firefox" / "firefox.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Mozilla Firefox" / "firefox.exe",
]


def create_browser() -> webdriver.Firefox:
    """
    Configura e inicializa a instância do WebDriver para Firefox com GeckoDriver.

    Variáveis de ambiente utilizadas:
    - GECKODRIVER_PATH: caminho relativo ou absoluto para o geckodriver.exe
    - FIREFOX_BINARY_PATH: caminho opcional para o executável do Firefox
    - FIREFOX_PROFILE_PATH: caminho opcional para o perfil do Firefox
    - HEADLESS: "true" para ocultar a janela ou "false" (padrão) para exibir o navegador na tela
    """
    geckodriver_env = os.getenv("GECKODRIVER_PATH", "./drivers/geckodriver.exe").strip()
    firefox_binary_env = os.getenv("FIREFOX_BINARY_PATH", "").strip()
    firefox_profile_env = os.getenv("FIREFOX_PROFILE_PATH", "").strip()
    download_dir_env = os.getenv("DOWNLOAD_DIR", "").strip()
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
        print("[AUTOMAÇÃO] Modo Headless ativado.")
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

        if profile_path.exists():
            # Verifica se o perfil está em uso (presença de parent.lock no Windows)
            lock_file = profile_path / "parent.lock"
            if lock_file.exists():
                print(
                    f"[AUTOMAÇÃO AVISO] O perfil '{profile_path.name}' está em uso pelo Firefox. "
                    "Para evitar recusa de conexão, abrindo em um perfil novo isolado."
                )
            else:
                options.profile = str(profile_path)
                use_profile = True
        else:
            print(f"[AUTOMAÇÃO AVISO] Diretório de perfil não encontrado: {profile_path}")

    service = Service(executable_path=str(geckodriver_path))

    try:
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    except Exception as exc:
        # Se falhou usando perfil, tenta sem o perfil como fallback automático
        if use_profile:
            print(f"[AUTOMAÇÃO AVISO] Falha ao abrir com o perfil configurado. Tentando abrir perfil isolado...")
            fallback_options = FirefoxOptions()
            _apply_download_preferences(fallback_options)
            if headless_env:
                fallback_options.add_argument("--headless")
            if options.binary_location:
                fallback_options.binary_location = options.binary_location
            driver = webdriver.Firefox(service=service, options=fallback_options)
            return driver
        raise exc


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
