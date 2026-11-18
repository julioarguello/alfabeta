# Spec 006's container read (amendment of 2026-11-17, FR-028). Built from the repository root:
#   docker build --platform linux/amd64 -f docker/classroom/Dockerfile -t alfabeta-classroom-read .
# so alfabeta's own extractor is copied unchanged. linux/amd64 is the platform research S14
# measured (under emulation on the Mac); Google Chrome is the browser S14's sign-ins used.
# The image holds no secret: the account and the password arrive on stdin at run time.
FROM python:3.12-slim-bookworm

RUN pip install --no-cache-dir playwright==1.64.1 && playwright install --with-deps chrome \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY docker/classroom/read.py /app/read.py
COPY skills/classroom-sync/scripts/extract.js /app/extract.js

ENV HOME=/tmp PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/app/read.py"]
