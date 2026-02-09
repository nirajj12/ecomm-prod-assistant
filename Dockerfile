FROM python:3.11-slim

WORKDIR /app

# install git (some deps may require it)
RUN apt-get update && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY prod_assistant ./prod_assistant

RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY data ./data
COPY static ./static
COPY templates ./templates
COPY main.py ./main.py
COPY scrapper_ui.py ./scrapper_ui.py

ENV PYTHONPATH="/app:/app/prod_assistant"

EXPOSE 8000

# run uvicorn properly on 0.0.0.0:8000
CMD ["bash", "-c", "python prod_assistant/mcp_servers/product_search_saver.py & uvicorn prod_assistant.router.main:app --host 0.0.0.0 --port 8000 --workers 1"]
