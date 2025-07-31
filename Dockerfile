FROM python:3.12-alpine
LABEL maintainer="Aaron Drydale <adrydale.dev@gmail.com>"
LABEL org.opencontainers.image.title="Outlan IPAM"
LABEL org.opencontainers.image.description="A minimal IP Address Management (IPAM) system"
LABEL org.opencontainers.image.source="https://github.com/adrydale/outlan"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user (let system assign UID/GID)
RUN addgroup outlan && \
    adduser -D -s /bin/sh -G outlan outlan

WORKDIR /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set proper permissions
RUN chmod +x entrypoint.sh && \
    chown -R outlan:outlan /app

# Switch to non-root user
USER outlan

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/api/health || exit 1

EXPOSE 5000
CMD ["./entrypoint.sh"]
