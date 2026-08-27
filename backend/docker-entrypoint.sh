#!/bin/sh
# Ponto de entrada do container do backend.
#
# Roda como root só até garantir que o volume persistente /data (montado pelo
# EasyPanel) exista com a estrutura esperada e o dono correto — um volume recém
# criado costuma vir vazio ou pertencendo a root, o que impediria o usuário
# não-root da aplicação de escrever nele. Depois disso, dropa privilégios com
# gosu e executa o comando real (uvicorn) como o usuário "servopa".
set -e

MAX_CONCURRENT_AUTOMATIONS="${MAX_CONCURRENT_AUTOMATIONS:-3}"

mkdir -p /data/firefox-profile /data/pdfs /data/logs /data/screenshots

# Pré-cria um perfil de Firefox e uma pasta de download por slot de execução
# simultânea (até MAX_CONCURRENT_AUTOMATIONS) — cada automação rodando ao
# mesmo tempo usa o seu próprio slot, isolado dos demais. O app também cria
# esses diretórios sozinho na primeira vez que usa um slot, então isto aqui é
# só para garantir o dono certo (servopa) desde o início.
i=1
while [ "$i" -le "$MAX_CONCURRENT_AUTOMATIONS" ]; do
    mkdir -p "/data/firefox-profile-slot${i}" "/data/pdfs/_downloads-slot${i}"
    i=$((i + 1))
done

chown -R servopa:servopa /data 2>/dev/null || true

exec gosu servopa "$@"
