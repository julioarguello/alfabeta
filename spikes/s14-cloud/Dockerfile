# Spike S14 (#166): the scripted sign-in and the whole read, in a container that runs where it can
# (the Mac's Docker from the home address; a Cloud Run job, where Google answered with a captcha).
# Python, the Playwright package pinned as on the Mac, and the installed Google Chrome with its system
# libraries, so the browser Google sees is the one the Mac run used. Google Chrome ships for amd64
# only: build with --platform linux/amd64.
#
# The build context is a folder the launchers assemble: s14_scripted_signin.py, s14_capture.py and
# alfabeta's own extractor (skills/classroom-sync/scripts/extract.js) as extract.js.
FROM python:3.12-slim-bookworm

RUN pip install --no-cache-dir playwright==1.64.1 && playwright install --with-deps chrome \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY s14_scripted_signin.py s14_capture.py extract.js /app/

# No file is kept but what a run writes to /out; the log is stdout.
ENV HOME=/tmp S14_STUDENT=cloud PYTHONUNBUFFERED=1
# Default: sign in and check the session. The whole read: `python /app/s14_capture.py`.
CMD ["sh", "-c", "python /app/s14_scripted_signin.py signin && python /app/s14_scripted_signin.py read"]
