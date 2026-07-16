COMPOSE ?= docker compose

.PHONY: help up build down logs ps restart config clean

help:
	@echo "UKRFLYBUD Manager"
	@echo "  make up       Build and start the local stack"
	@echo "  make build    Build all service images"
	@echo "  make down     Stop local services"
	@echo "  make logs     Follow service logs"
	@echo "  make ps       Show service status"
	@echo "  make config   Validate Docker Compose configuration"
	@echo "  make restart  Restart the local stack"
	@echo "  make clean    Stop services and remove local volumes"

up:
	$(COMPOSE) up --build

build:
	$(COMPOSE) build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

config:
	$(COMPOSE) config

restart:
	$(COMPOSE) down
	$(COMPOSE) up --build

clean:
	$(COMPOSE) down -v --remove-orphans
