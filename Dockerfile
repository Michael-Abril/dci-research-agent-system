FROM python:3.11-slim

WORKDIR /app

# System dependencies for PyMuPDF
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libmupdf-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Create data directories if they don't exist
RUN mkdir -p data/documents/{cbdc,privacy,stablecoins,payment_tokens,bitcoin,general} \
            data/indexes/{cbdc,privacy,stablecoins,payment_tokens,bitcoin}

# Expose both Streamlit and FastAPI ports
EXPOSE 8501 8000

# Health check (supports either service)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || \
                 curl --fail http://localhost:8000/api/health || exit 1

# Default: run Streamlit UI
# Override with: docker run ... dci-agent uvicorn api.main:app --host 0.0.0.0 --port 8000
ENTRYPOINT ["streamlit", "run", "app/main.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true"]
