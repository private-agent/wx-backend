#!/bin/bash

# 删除旧的容器
docker compose down
docker rmi $(basename "$(dirname "$(realpath "$0")")")-main
docker compose up $@
docker compose logs -f 2>/dev/null
