FROM python:slim-bookworm

WORKDIR /app
COPY spotify_to_jellyfin requirements.txt spotifin_discord.py /app/

RUN apt-get update && apt-get install -y git ffmpeg && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

ENV MUSIC_LIBRARY_PATH=/music

CMD ["python", "spotifin_discord.py"]