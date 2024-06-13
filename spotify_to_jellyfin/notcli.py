import os
import json
import logging

from .downloader import Downloader
from .downloader_song import DownloaderSong
from .spotify_api import SpotifyApi
from .jellyfin import JellyfinApi
from .models import Lyrics
from pathlib import Path


def request_music(
    url: str, discord_id: int, output_path: str, playlist_public: bool = False
):
    third_party_lyrics = True
    print_exceptions = True
    overwrite = False
    logging.basicConfig(
        format="[%(levelname)-8s %(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    logger.setLevel("INFO")
    logger.debug("Starting downloader")
    sp_dc_cookie = os.getenv("SP_DC_COOKIE")
    if not sp_dc_cookie:
        logger.critical("Environment variable for sp_dc_cookie not found")
        return
    spotify_api = SpotifyApi(sp_dc_cookie)
    jellyfin_api = JellyfinApi(os.getenv("JELLYFIN_URL"), os.getenv("JELLYFIN_API_KEY"))
    downloader = Downloader(
        spotify_api,
        Path(output_path),
    )
    downloader_song = DownloaderSong(
        downloader,
        premium_quality=spotify_api.is_premium,
    )
    if not spotify_api.is_premium:
        logger.warning("Free account detected. Premium features are unavailable")
    logger.debug("Setting up CDM")
    downloader.set_cdm()
    if not downloader.ffmpeg_path_full:
        logger.critical("ffmpeg not found")
        return
    error_count = 0
    pathslist = []
    try:
        url_info = downloader.get_url_info(url)
        download_queue = downloader.get_download_queue(url_info)
    except Exception as e:
        error_count += 1
        logger.error(
            f'Failed to check "{url}"',
            exc_info=print_exceptions,
        )
        return
    for queue_index, queue_item in enumerate(download_queue, start=1):
        queue_progress = f"Track {queue_index}/{len(download_queue)}"
        track = queue_item.metadata
        try:
            logger.info(f'({queue_progress}) Downloading "{track["name"]}"')
            track_id = track["id"]
            logger.debug("Getting GID metadata")
            gid = spotify_api.track_id_to_gid(track_id)
            metadata_gid = spotify_api.get_gid_metadata(gid)
            if not metadata_gid.get("original_video"):
                logger.debug("Getting album metadata")
                album_metadata = spotify_api.get_album(
                    spotify_api.gid_to_track_id(metadata_gid["album"]["gid"])
                )
                logger.debug("Getting track credits")
                track_credits = spotify_api.get_track_credits(track_id)
                tags = downloader_song.get_tags(
                    metadata_gid, album_metadata, track_credits
                )
                if metadata_gid.get("has_lyrics") and spotify_api.is_premium:
                    lyrics = downloader_song.get_lyrics(track_id)
                else:
                    lyrics = Lyrics
                if not lyrics.synced and third_party_lyrics:
                    logger.debug("Getting third-party lyrics")
                    try:
                        logger.debug(
                            f"Searching third-party lyrics for {tags['artist']} - {tags['title']}"
                        )
                        tp_lyrics = downloader_song.get_third_party_lyrics(
                            tags["title"], tags["artist"]
                        )
                    except Exception as e:
                        logger.error(
                            f"({queue_progress}) Failed to get third-party lyrics {e}",
                            exc_info=print_exceptions,
                        )
                    if tp_lyrics.synced or not lyrics.unsynced:
                        lyrics = tp_lyrics
                tags["lyrics"] = lyrics.unsynced
                final_path = downloader_song.get_final_path(tags)
                pathslist.append(final_path)
                lrc_path = downloader_song.get_lrc_path(final_path)
                cover_path = downloader_song.get_cover_path(final_path)
                cover_url = downloader.get_cover_url(metadata_gid, "LARGE")
                if final_path.exists() and not overwrite:
                    logger.warning(
                        f'({queue_progress}) Track already exists at "{final_path}", skipping'
                    )
                else:
                    logger.debug("Getting file info")
                    file_id = downloader_song.get_file_id(metadata_gid)
                    if not file_id:
                        logger.error(
                            f"({queue_progress}) Track not available on Spotify's "
                            "servers and no alternative found, skipping"
                        )
                        continue
                    logger.debug("Getting PSSH")
                    pssh = spotify_api.get_pssh(file_id)
                    logger.debug("Getting decryption key")
                    decryption_key = downloader_song.get_decryption_key(pssh)
                    logger.debug("Getting stream URL")
                    stream_url = spotify_api.get_stream_url(file_id)
                    encrypted_path = downloader.get_encrypted_path(track_id, ".m4a")
                    decrypted_path = downloader.get_decrypted_path(track_id, ".m4a")
                    logger.debug(f'Downloading to "{encrypted_path}"')
                    downloader_song.download(encrypted_path, stream_url)
                    remuxed_path = downloader.get_remuxed_path(track_id, ".m4a")
                    logger.debug(f'Decrypting/Remuxing to "{remuxed_path}"')
                    downloader_song.remux(
                        encrypted_path,
                        decrypted_path,
                        remuxed_path,
                        decryption_key,
                    )
                    logger.debug("Applying tags")
                    downloader.apply_tags(remuxed_path, tags, cover_url)
                    logger.debug(f'Moving to "{final_path}"')
                    downloader.move_to_final_path(remuxed_path, final_path)
                if not lyrics.synced:
                    pass
                elif lrc_path.exists() and not overwrite:
                    logger.debug(
                        f'Synced lyrics already exists at "{lrc_path}", skipping'
                    )
                else:
                    logger.debug(f'Saving synced lyrics to "{lrc_path}"')
                    downloader_song.save_lrc(lrc_path, lyrics.synced)
            else:
                logger.error(
                    f"({queue_progress}) Cannot download music videos to jellyfin, skipping"
                )
        except Exception as e:
            error_count += 1
            logger.error(
                f'({queue_progress}) Failed to download "{track["name"]}"',
                exc_info=print_exceptions,
            )
        finally:
            if downloader.temp_path.exists():
                logger.debug(f'Cleaning up "{downloader.temp_path}"')
                downloader.cleanup_temp_path()
    if url_info.type == "playlist" and discord_id:
        playlist_name = spotify_api.get_playlist(url_info.id)["name"]
        print(f'Trying to sync playlist "{playlist_name}" to jellyfin')
        if os.path.exists("./config/playlists.json"):
            with open("./config/playlists.json", "r") as f:
                playlist_lookup = json.load(f)
        else:
            playlist_lookup = {}
        jellyfin_api.refresh_library()
        song_ids = []
        for path in pathslist:
            song_ids.append(jellyfin_api.lookup_song_id(str(path)))
        if url_info.id in playlist_lookup:
            jellyfin_playlist_id = playlist_lookup[url_info.id]
            jellyfin_api.update_playlist(jellyfin_playlist_id, playlist_name, song_ids)
        else:
            jellyfin_playlist_id = jellyfin_api.create_playlist(
                playlist_name,
                song_ids,
                jellyfin_api.lookup_jellyfin_userid(discord_id),
                playlist_public,
            )
            playlist_lookup[url_info.id] = jellyfin_playlist_id
            with open("./config/playlists.json", "w") as f:
                json.dump(playlist_lookup, f, indent=4)
    logger.info(f"Done ({error_count} error(s))")
