FROM mcr.microsoft.com/playwright/python:v1.56.0-noble

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y git ffmpeg xvfb

RUN python -m pip install --upgrade pip

RUN pip install .

RUN python -m playwright install chromium

RUN rip config path 

ENTRYPOINT ["cabot"]