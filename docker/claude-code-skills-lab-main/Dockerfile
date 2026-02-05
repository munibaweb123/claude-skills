ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-alpine

# ARG value is accessible here during build
RUN echo "Building with Python ${PYTHON_VERSION}"

# But NOT accessible at runtime
# The following would fail because ARG is gone after build:
# CMD ["echo", "${PYTHON_VERSION}"]

# Create user
RUN adduser -D -u 1000 appuser

# ... copy files with ownership ...

# Switch to non-root user BEFORE CMD
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Copy with ownership set to appuser
COPY --chown=appuser:appuser main.py .