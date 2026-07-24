FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRADING_MODE=PAPER \
    LIVE_EQUITIES_ENABLED=false \
    LIVE_CRYPTO_ENABLED=false \
    AUTONOMOUS_EXECUTION_ENABLED=false

WORKDIR /app
RUN groupadd --system quantdesk && useradd --system --gid quantdesk quantdesk
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY apps ./apps
COPY dashboard ./dashboard
COPY reports ./reports
COPY migrations ./migrations
COPY alembic.ini ./
RUN chown -R quantdesk:quantdesk /app
USER quantdesk

EXPOSE 8000
CMD ["uvicorn", "quant_trade_desk.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
