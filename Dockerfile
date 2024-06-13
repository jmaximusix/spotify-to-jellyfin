FROM python:slim-bookworm

RUN apt-get update && apt-get install -y git ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY spotify_to_jellyfin/ spotifin_discord.py requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

ENV MUSIC_LIBRARY_PATH=/music

CMD ["python", "spotifin_discord.py"]