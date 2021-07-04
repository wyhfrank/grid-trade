build:
	docker build . -t gridbot

run:
	docker run --rm --name gridbot -v `pwd`/configs:/app/configs gridbot python main.py configs/config.yml
