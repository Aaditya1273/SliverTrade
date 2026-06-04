FROM prom/alertmanager:latest

# Install shell utilities needed by the entrypoint script
RUN apk add --no-cache sed

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
