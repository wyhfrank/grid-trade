FROM python:3.9-slim-buster

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .