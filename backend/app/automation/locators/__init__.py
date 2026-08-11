"""
Locators do site Servopa — Page Object Pattern
===============================================
Centraliza todos os seletores (IDs, XPaths, CSS) usados pelo Selenium para
interagir com o site da Servopa.

Se o site mudar um id ou classe, basta corrigir aqui, sem tocar no código
de automação.

Estrutura:
  ServopaLocators       — login e elementos gerais
  ServopaGroupLocators  — busca de grupo/cota/dígito
  ServopaLanceLocators  — oferta de lances e modais
"""

from selenium.webdriver.common.by import By  # type: ignore


class ServopaLocators:
    """Localizadores para login e elementos gerais do site."""

    # Campo CPF/CNPJ do formulário de login
    USERNAME_FIELD = (By.ID, "representante_cpf_cnpj")

    # Campo senha do formulário de login
    PASSWORD_FIELD = (By.ID, "representante_senha")

    # Botão de submissão do formulário de login
    LOGIN_BUTTON = (By.ID, "btn_representante")

    # Mensagem de erro exibida quando CPF/CNPJ ou senha são inválidos
    LOGIN_ERROR_MESSAGE = (
        By.XPATH,
        "//div[@class='error' and contains(text(), 'CPF/CNPJ ou senha inválidos!')]",
    )

    # Overlay de carregamento exibido durante transições de página
    LOADING_OVERLAY = (By.CLASS_NAME, "loading-overlay")

    # Widget de captcha ("Confirme que é humano")
    CAPTCHA = (By.XPATH, "//span[contains(text(), 'Confirme que é humano')]")

    # Link/botão de logout
    LOGOUT_BUTTON = (By.XPATH, "//a[contains(@href, 'logout')]")

    # Logo da navegação principal — clicando volta à página inicial
    HOME_LOGO_LINK = (
        By.XPATH,
        "//aside[@id='main-nav']//img[@alt='Consórcio Servopa']",
    )


class ServopaGroupLocators:
    """Localizadores para a página de busca de grupo."""

    # Campo de número do grupo
    GROUP_INPUT = (By.ID, "grupo")

    # Campo de número da cota (plano)
    COTA_INPUT = (By.ID, "plano")

    # Campo de dígito verificador da cota
    DIGITO_INPUT = (By.ID, "digito")

    # Botão para disparar a busca do grupo/cota/dígito
    SEARCH_GROUP_BUTTON = (By.ID, "btn_busca_usuario")


class ServopaLanceLocators:
    """Localizadores para a página de oferta de lances."""

    # ── Erros e avisos ───────────────────────────────────────────────────────

    # Erro específico: cota já contemplada
    LANCE_CONTEMPLADO_ERROR = (
        By.XPATH,
        "//section[@class='main-view']"
        "//div[contains(@class, 'message-block') and contains(@class, 'error')"
        " and contains(., 'Cota já está contemplada')]",
    )

    # Bloco de erro genérico na página de lances (ex.: "sem lances na assembleia")
    LANCE_ERROR_BLOCK = (By.CSS_SELECTOR, "div.message-block.error")

    # ── Abas de tipo de lance ────────────────────────────────────────────────

    LANCE_FIDELIDADE_TAB = (
        By.XPATH,
        "//div[@class='tab-switcher']//a[text()='Fidelidade']",
    )
    LANCE_FIXO_TAB = (By.XPATH, "//div[@class='tab-switcher']//a[text()='Fixo']")
    LANCE_LIVRE_TAB = (By.XPATH, "//div[@class='tab-switcher']//a[text()='Livre']")

    # Seletor alternativo usando atributo data-lance
    LANCE_LIVRE_TAB_DATA = (By.CSS_SELECTOR, ".tab-switcher a[data-lance='L']")

    # Aba atualmente ativa
    LANCE_ACTIVE_TAB = (By.CSS_SELECTOR, ".tab-switcher a.active")

    # ── Campos de lance livre ────────────────────────────────────────────────

    # Alguns ambientes usam "L" maiúsculo, outros minúsculo — ambos mapeados
    LANCE_LIVRE_PERCENTUAL_INPUT = (By.ID, "tx_Lanliv")
    LANCE_LIVRE_PERCENTUAL_INPUT_ALT = (By.ID, "tx_lanliv")

    # Campo de lance embutido a descontar
    LANCE_LIVRE_DESCONTAR_INPUT = (By.ID, "tx_lanliv_emb")

    # ── Outros campos ────────────────────────────────────────────────────────

    # Campo de número de protocolo anterior
    PROTOCOLO_ANTERIOR_INPUT = (By.ID, "num_protocolo_ant")

    # Nome do consorciado exibido na página
    NOME_CLIENTE_TEXT = (
        By.XPATH,
        "//span[text()='Consorciado']/following-sibling::h3[1]",
    )

    # ── Cabeçalhos de extrato ────────────────────────────────────────────────

    # Extrato cancelado
    EXTRATO_CANCELADO_HEADER = (
        By.XPATH,
        "//section[@class='main-view']/div[@class='header']"
        "/h2[starts-with(normalize-space(.), 'Extrato - Cancelado')]",
    )

    # Extrato normal
    EXTRATO_HEADER_NORMAL = (
        By.XPATH,
        "//section[@class='main-view']/div[@class='header']"
        "/h2[normalize-space(.)='Extrato']",
    )

    # Qualquer cabeçalho de extrato (normal ou cancelado)
    EXTRATO_HEADER_ANY = (
        By.XPATH,
        "//section[@class='main-view']/div[@class='header']"
        "/h2[starts-with(normalize-space(.), 'Extrato')]",
    )

    # ── Botões principais ────────────────────────────────────────────────────

    # Link "Ofertar Lance" na listagem de cotas
    OFERTAR_LANCE_BUTTON = (By.XPATH, "//a[contains(., 'Ofertar Lance')]")

    # Botão de simulação de lance
    SIMULAR_BUTTON = (By.ID, "btn_simular")

    # Botão "Registrar" — pode ser <button> ou <a>; mantemos múltiplos seletores
    REGISTRAR_BUTTON = (
        By.XPATH,
        "//button[contains(normalize-space(.), 'Registrar')]",
    )
    REGISTRAR_LINK = (By.XPATH, "//a[normalize-space(.)='Registrar']")

    # XPath absoluto como último recurso (fallback)
    REGISTRAR_ABSOLUTE = (
        By.XPATH,
        "/html/body/main/section/div[2]/div/div/div[2]/form/div[6]/a[1]",
    )

    # ── Modal de bloqueio de assembleia (SweetAlert2 / custom) ──────────────

    MODAL_CONTAINER = (
        By.CSS_SELECTOR,
        ".swal2-container, .sweet-alert, .swal2-popup",
    )
    MODAL_TEXT = (
        By.CSS_SELECTOR,
        ".swal2-container .swal2-html-container, .swal2-content, .sweet-alert p",
    )
    MODAL_OK_BUTTON = (By.CSS_SELECTOR, ".swal2-confirm, .confirm")
    MODAL_OK_BUTTON_BY_TEXT = (
        By.XPATH,
        "//button[normalize-space(.)='OK' or normalize-space(.)='Ok' or normalize-space(.)='ok']",
    )

    # ── Opções de lance embutido ─────────────────────────────────────────────

    LANCE_EMBUTIDO_OPTIONS_CONTAINER = (By.ID, "lansetxt")
