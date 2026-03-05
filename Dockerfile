FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /app

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir .

CMD ["coloursorter-bench-cli", "--scenario", "nominal", "--avg-rtt-ms", "9", "--peak-rtt-ms", "15"]
