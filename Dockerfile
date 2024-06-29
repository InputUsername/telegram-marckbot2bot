FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /data

ENV STATE_DIRECTORY=/data

VOLUME /data

COPY . .

CMD ["python", "-m", "marckbot2bot"]
