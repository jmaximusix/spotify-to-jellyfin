import os
import json
import requests
import time


class JellyfinApi:
    def __init__(self, base_url: str, api_token: str):
        self.auth = {"Authorization": f'MediaBrowser Token="{api_token}"'}
        self.base_url = base_url
        if not os.path.exists("./config/users.json"):
            print(
                "[Jellyfin API] No users.json found, creating one. Remember to fill in the discord ids."
            )
            jellyfin_users = requests.get(f"{base_url}/Users", headers=self.auth).json()
            self.users = []
            for user in jellyfin_users:
                self.users.append(
                    {
                        "name": user["Name"],
                        "jellyfin_id": user["Id"],
                        "discord_id": None,
                    }
                )
            with open("./config/users.json", "w") as f:
                json.dump(self.users, f, indent=4)
        else:
            with open("./config/users.json", "r") as f:
                self.users = json.load(f)

    def lookup_jellyfin_userid(self, discord_id: int) -> str:
        assert discord_id is not None, "Valid discord id required"
        for user in self.users:
            if user["discord_id"] == discord_id:
                return user["jellyfin_id"]
        raise ValueError("User not found in users.json")

    def lookup_song_id(self, path: str) -> str:
        relative_path = path.rsplit("/", maxsplit=3)[1:]
        title = " ".join(relative_path[2][:-4].split(" ")[1:])
        searchTerm = longest_ascii_substring(title)
        search_res = requests.get(
                f"{self.base_url}/Items?searchTerm={searchTerm}&includeItemTypes=Audio&Recursive=true&fields=Path",
                headers=self.auth,
            ).json()["Items"]
        for song in search_res:
            relative_song_path = song["Path"].rsplit("/", maxsplit=3)[1:]
            if relative_path == relative_song_path:
                return song["Id"]
        raise ValueError(f"Couldn't find song in Jellyfin: {title}")

    def create_playlist(
        self,
        playlist_name: str,
        songs: list[str],
        jellyfin_id: str,
        public: bool = False,
    ):
        body = {
            "Name": playlist_name,
            "Ids": songs,
            "UserId": jellyfin_id,
            "MediaType": "Audio",
            # Works but currently not implemented
            # "Users": [
            #     {"UserId": "1741114c47c04c619998619b2ac0ebdf", "CanEdit": True},
            #     {"UserId": "4ef98e9e710d4610a921480c92ca1896", "CanEdit": False},
            # ],
            "IsPublic": public,
        }
        response = requests.post(
            f"{self.base_url}/Playlists", headers=self.auth, json=body
        ).json()
        return response["Id"]

    def update_playlist(
        self,
        playlist_id: str,
        playlist_name: str,
        songs: list[str],
        public: bool = False,
    ) -> None:
        raise Exception(
            "Updating existing playlists is not supported because of jellyfin bug #12092"
        )
        body = {
            "Name": playlist_name,
            "Ids": songs,
            "IsPublic": public,
        }
        response = requests.post(
            f"{self.base_url}/Playlists/{playlist_id}",
            headers=self.auth,
            json=body,
        )
        assert response.status_code == 204, "Failed to update playlist"

    def refresh_library(self) -> None:
        requests.post(f"{self.base_url}/Library/Refresh", headers=self.auth)
        time.sleep(10)


def longest_ascii_substring(s: str) -> str:
    longest_substring = ""
    current_substring = ""

    for char in s:
        if ord(char) < 128:  # ASCII characters have an ordinal value less than 128
            current_substring += char
            if len(current_substring) > len(longest_substring):
                longest_substring = current_substring
        else:
            current_substring = ""

    return longest_substring
