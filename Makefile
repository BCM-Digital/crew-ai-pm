.PHONY: bootstrap synth deploy db\:migrate smoke test lint format security clean

bootstrap:
	pnpm i -w
	pip install -r requirements.txt

synth:
	cd infra/cdk && pnpm cdk synth

deploy:
	cd infra/cdk && pnpm cdk deploy --all --require-approval never

db\:migrate:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "ERROR: DATABASE_URL not set"; \
		exit 1; \
	fi
	psql $$DATABASE_URL -f runtime/db/sql/001_init.sql
	psql $$DATABASE_URL -f runtime/db/sql/002_indexes.sql

smoke:
	bash tests/smoke/smoke_planday.sh

test:
	pytest tests/ -v
	cd infra/cdk && pnpm test

lint:
	flake8 lambdas/ runtime/ tests/ --max-line-length=100 --extend-ignore=E203
	cd infra/cdk && pnpm lint
	cd ui && pnpm lint

format:
	black lambdas/ runtime/ tests/ --line-length=100
	isort lambdas/ runtime/ tests/ --profile=black
	prettier --write "**/*.{ts,tsx,js,jsx,json,yaml,yml,md}"

security:
	bandit -r lambdas/ runtime/ -ll
	cd infra/cdk && pnpm audit
	cd ui && pnpm audit
	pip-audit

clean:
	rm -rf cdk.out .next .pytest_cache __pycache__ **/__pycache__ *.egg-info dist build
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
