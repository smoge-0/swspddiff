# Speed Race Discord bot — self-contained image.
# The monster database and name mapping live in the parent repo and are
# mounted read-only at runtime (see docker-compose.yml), so this image only
# needs the bot code — build context is this directory.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/speedrace_bot

# install deps first so requirement changes don't invalidate the app layer
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# non-root runtime user; data/ is the swarfarm cache (persisted via volume).
# Named volumes inherit the image directory's ownership on first use, so
# chown here makes the mounted cache writable by the bot.
RUN mkdir -p /app/speedrace_bot/data \
    && useradd --create-home --uid 1000 bot \
    && chown -R bot:bot /app/speedrace_bot

USER bot

CMD ["python", "-u", "bot.py"]
