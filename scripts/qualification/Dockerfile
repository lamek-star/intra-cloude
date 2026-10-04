FROM intraforge-local-runtime:qualification
USER root
COPY apps/backend/requirements/dev.txt /tmp/qualification-requirements.txt
RUN pip install --no-cache-dir -r /tmp/qualification-requirements.txt
USER app
