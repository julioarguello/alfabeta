# Spike S14 in Google Cloud (#166): the same scripted sign-in, from a Cloud Run job.
# Python, the Playwright package pinned as on the Mac, and the installed Google Chrome with its system
# libraries, so the browser Google sees is the one the Mac run used. Google Chrome ships for amd64
# only: build with --platform linux/amd64 (Cloud Run's platform).
FROM python:3.12-slim-bookworm

RUN pip install --no-cache-dir playwright==1.64.1 && playwright install --with-deps chrome \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY s14_scripted_signin.py /app/s14_scripted_signin.py

# No file is kept: the container's disk goes when the job ends, and the log is stdout (Cloud Logging).
ENV HOME=/tmp S14_STUDENT=cloud PYTHONUNBUFFERED=1
ENTRYPOINT ["sh", "-c", "python /app/s14_scripted_signin.py signin && python /app/s14_scripted_signin.py read"]
