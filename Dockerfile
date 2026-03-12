FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Optimization: Bytecode and Cache
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into the system python (best for Playwright Docker)
RUN uv sync --no-dev --frozen
RUN uv run playwright install chromium --with-deps

# Copy the rest of the code
COPY . .

# Ensure the user_data directory exists and has permissions
RUN mkdir -p /app/user_data && chmod 777 /app/user_data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]