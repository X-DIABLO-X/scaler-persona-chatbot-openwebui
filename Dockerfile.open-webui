FROM ghcr.io/open-webui/open-webui:main-slim

COPY services/open-webui/render-entrypoint.sh /render-entrypoint.sh

RUN chmod +x /render-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/render-entrypoint.sh"]
