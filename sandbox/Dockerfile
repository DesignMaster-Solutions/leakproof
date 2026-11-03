# The image every untrusted run uses. No secrets, no network tools, non-root.
# Base pinned by digest (python:3.12-slim, pulled 2026-11-03) so receipts stay reproducible.
FROM python@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
RUN pip install --no-cache-dir "pandas==2.2.3" && \
    rm -rf /root/.cache && \
    useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin runner
COPY sitecustomize.py /usr/local/lib/python3.12/site-packages/sitecustomize.py
USER 10001
WORKDIR /out
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
