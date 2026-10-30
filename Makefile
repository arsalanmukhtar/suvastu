.PHONY: up down reset logs psql ps creds s1-search reaches worker-shell build-prod

up:
	docker compose up -d --build

down:
	docker compose down

reset:            ## wipe DB volume and re-run init SQL
	docker compose down -v && docker compose up -d --build

logs:
	docker compose logs -f api web

ps:
	docker compose ps

psql:
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

creds:            ## verify Earthdata + HyP3 credentials
	docker compose run --rm worker suvastu.hyp3_jobs credits

s1-search:
	docker compose run --rm worker suvastu.search_s1 --level SLC

reaches:          ## segment the Swat main stem into 500 m reaches
	docker compose run --rm worker suvastu.build_reaches

worker-shell:
	docker compose run --rm --entrypoint bash worker

build-prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
