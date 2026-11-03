# The image every untrusted run uses. No secrets, no network tools, non-root.
FROM python:3.12-slim
RUN pip install --no-cache-dir "pandas==2.2.3" && \
    rm -rf /root/.cache && \
    useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin runner
COPY sitecustomize.py /usr/local/lib/python3.12/site-packages/sitecustomize.py
USER 10001
WORKDIR /out
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
