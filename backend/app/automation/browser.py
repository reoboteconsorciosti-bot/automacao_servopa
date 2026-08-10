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
    """
    geckodriver_env = os.getenv("GECKODRIVER_PATH", "./drivers/geckodriver.exe").strip()
    firefox_binary_env = os.getenv("FIREFOX_BINARY_PATH", "").strip()
    firefox_profile_env = os.getenv("FIREFOX_PROFILE_PATH", "").strip()

    # Resolve o caminho do GeckoDriver
    geckodriver_path = Path(geckodriver_env)
    if not geckodriver_path.is_absolute():
        geckodriver_path = (BASE_DIR / geckodriver_path).resolve()

    options = FirefoxOptions()

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

    # Configura o perfil do Firefox apenas se especificado no .env
    if firefox_profile_env:
        profile_path = Path(firefox_profile_env)
        if not profile_path.is_absolute():
            profile_path = (BASE_DIR / profile_path).resolve()
        options.profile = str(profile_path)

    service = Service(executable_path=str(geckodriver_path))

    driver = webdriver.Firefox(service=service, options=options)
    return driver


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
