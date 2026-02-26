# Rutas relativas desde la raíz
COMPOSE_FILE=deploy/docker/docker-compose.yaml
ENV_FILE=deploy/.env

.PHONY: up down shell logs

up:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d --remove-orphans trainer

down:
	docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) down

shell:
	docker exec -it aegf_trainer /bin/bash

logs:
	docker exec -it aegf_trainer docker logs -f aegf_trainer