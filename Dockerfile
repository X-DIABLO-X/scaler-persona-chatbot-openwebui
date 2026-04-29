FROM ghcr.io/open-webui/open-webui:main

COPY services/open-webui/render-entrypoint.sh /render-entrypoint.sh

RUN chmod +x /render-entrypoint.sh

ENTRYPOINT ["/render-entrypoint.sh"]
