ARG BUILD_FROM=ghcr.io/hassio-addons/base-python:14.0.2
FROM ${BUILD_FROM}

RUN apk add --no-cache nodejs npm tzdata

WORKDIR /opt/web
COPY web /opt/web
RUN npm install && npm run build

RUN mkdir -p /app/static && cp -r /opt/web/dist/* /app/static/

WORKDIR /app
COPY backend /app/backend
COPY config.yaml /app/config.yaml

RUN pip install --no-cache-dir fastapi uvicorn[standard] aiohttp pydantic pydantic-settings paho-mqtt

EXPOSE 8100
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8100"]
