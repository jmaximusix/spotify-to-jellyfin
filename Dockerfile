FROM python:slim-bookworm

RUN apt-get update && apt-get install -y git ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY spotify_to_jellyfin/ /app/spotify_to_jellyfin
COPY spotifin_discord.py /app/

RUN chown -R 1000:1000 /app

ENV MUSIC_LIBRARY_PATH=/music

CMD ["python", "spotifin_discord.py"]