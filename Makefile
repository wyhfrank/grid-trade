build:
	docker-compose build

up:
	docker-compose up --rm

rm:
	docker rm gridbot

build_old:
	docker build . -t gridbot

run_old:
	docker run --rm --name gridbot \
		-v `pwd`/configs:/app/configs \
		-v `pwd`/logs:/app/logs \
		-v /etc/timezone:/etc/timezone:ro \
		gridbot python main.py configs/config.yml
