.PHONY: install train run test lint docker-up docker-down k8s-apply k8s-delete

install:
	pip install -r requirements-dev.txt

train:
	python -m ml.train

run: train
	uvicorn app.main:app --reload

test:
	python -m pytest

lint:
	ruff check .

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

# needs a secret first, see k8s/secret.example.yaml
k8s-apply:
	kubectl apply -k k8s/

k8s-delete:
	kubectl delete -k k8s/
