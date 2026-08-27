# syntax=docker/dockerfile:1
#
# Imagem de produção do backend (FastAPI + Selenium/Firefox headless).
#
# Diferente do desenvolvimento local no Windows (que usa Firefox + geckodriver.exe
# instalados na máquina, apontados via .env), esta imagem instala Firefox ESR e
# GeckoDriver para Linux dentro do próprio container — o navegador NÃO depende de
# nada instalado na máquina de quem acessa o sistema, só do backend no servidor.
#
# app/automation/browser.py continua lendo tudo via os.getenv(); os valores abaixo
# (ENV) são apenas defaults sensatos para este ambiente Linux/Docker e podem ser
# sobrescritos por variáveis configuradas no EasyPanel.

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Firefox ESR via pacote oficial do Debian.
# fonts-liberation evita glifos ausentes ao renderizar páginas; gosu é usado pelo
# entrypoint para rodar a aplicação como usuário não-root; wget baixa o GeckoDriver.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        firefox-esr \
        fonts-liberation \
        ca-certificates \
        gosu \
        wget \
    && rm -rf /var/lib/apt/lists/*

# GeckoDriver para Linux — não existe como pacote apt no Debian, então é baixado
# diretamente do release oficial no GitHub (conforme pedido). Detecta a arquitetura
# do host de build (amd64/arm64) para funcionar tanto em servidores comuns quanto ARM.
ARG GECKODRIVER_VERSION=0.37.1
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) gecko_arch="linux64" ;; \
        arm64) gecko_arch="linux-aarch64" ;; \
        *) echo "Arquitetura não suportada para GeckoDriver: $arch" >&2; exit 1 ;; \
    esac; \
    wget -q -O /tmp/geckodriver.tar.gz \
        "https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-${gecko_arch}.tar.gz"; \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/; \
    chmod +x /usr/local/bin/geckodriver; \
    rm /tmp/geckodriver.tar.gz

WORKDIR /app

# Dependências Python numa camada separada do código-fonte (cache de build)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação
COPY . .

# Usuário dedicado, não-root, para rodar a aplicação e o Firefox
RUN groupadd --system --gid 1001 servopa \
    && useradd --system --uid 1001 --gid servopa --home-dir /app --shell /usr/sbin/nologin servopa \
    && chown -R servopa:servopa /app

RUN chmod +x /app/docker-entrypoint.sh

# Defaults para o ambiente Linux/Docker. LANCES_DIR e DOWNLOAD_DIR ficam dentro de
# /data/pdfs (mesmo volume) para que mover o PDF do download bruto para a pasta
# final organizada por consultor seja uma operação barata no mesmo filesystem.
# Sobrescreva qualquer um destes valores nas variáveis de ambiente do EasyPanel.
ENV FIREFOX_BINARY_PATH=/usr/bin/firefox-esr \
    GECKODRIVER_PATH=/usr/local/bin/geckodriver \
    FIREFOX_PROFILE_PATH=/data/firefox-profile \
    DOWNLOAD_DIR=/data/pdfs/_downloads \
    LANCES_DIR=/data/pdfs \
    ERROS_FILE=/data/logs/erros_lances.txt \
    HEADLESS=true \
    PORT=8000 \
    MAX_CONCURRENT_AUTOMATIONS=3

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
