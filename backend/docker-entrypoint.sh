#!/bin/sh
# Ponto de entrada do container do backend.
#
# Roda como root só até garantir que o volume persistente /data (montado pelo
# EasyPanel) exista com a estrutura esperada e o dono correto — um volume recém
# criado costuma vir vazio ou pertencendo a root, o que impediria o usuário
# não-root da aplicação de escrever nele. Depois disso, dropa privilégios com
# gosu e executa o comando real (uvicorn) como o usuário "servopa".
set -e

mkdir -p /data/firefox-profile /data/pdfs /data/logs /data/screenshots
chown -R servopa:servopa /data 2>/dev/null || true

exec gosu servopa "$@"
