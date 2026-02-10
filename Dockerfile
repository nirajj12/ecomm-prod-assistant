FROM python:3.11-slim

WORKDIR /app

# instal git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY prod_assistant ./prod_assistant

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# run uvicorn properly on 0.0.0.0:8000
# Ensure MCP does not read platform PORT (8000) and collide with uvicorn.
CMD ["bash", "-c", "PORT=8001 MCP_PORT=8001 MCP_SERVER_PORT=8001 python -m prod_assistant.mcp_servers.product_search_saver & uvicorn prod_assistant.router.main:app --host 0.0.0.0 --port 8000 --workers 2"]
