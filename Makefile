build:
	docker build . -t gridbot

run:
	docker run --rm --name gridbot -v `pwd`/config.yml:/app/config.yml gridbot python main.py
