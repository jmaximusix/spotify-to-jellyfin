import os
import requests
import json


class JellyfinApi:
    def __init__(self, base_url: str, api_token: str):
        self.auth = {"Authorization": f'MediaBrowser Token="{api_token}"'}
        self.base_url = base_url
        if not os.path.exists("users.json"):
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
            with open("users.json", "w") as f:
                json.dump(self.users, f, indent=4)
        else:
            with open("users.json", "r") as f:
                self.users = json.load(f)

    def lookup_jellyfin_userid(self, discord_id: str) -> str:
        for user in self.users:
            if user["discord_id"] == discord_id:
                return user["jellyfin_id"]
        raise ValueError("User not found in users.json")

    def lookup_song_id(self, path: str) -> str:
        relative_path = path.rsplit("/", maxsplit=3)[1:]
        title = relative_path[2][3:-4]
        song = requests.get(
            f"{self.base_url}/Items?searchTerm={title}&includeItemTypes=Audio&Recursive=true&fields=Path",
            headers=self.auth,
        ).json()["Items"][0]
        relative_song_path = song["Path"].rsplit("/", maxsplit=3)[1:]
        assert relative_path == relative_song_path, "Couldn't find song in Jellyfin"
        return song["Id"]

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


# print(
#     lookup_jellyfin_id(
#         "/soos/yeet/Florian Paul & Die Kapelle der letzten H/Dazwischen/09 Bella Maria.m4a"
#     )
# )

bella_maria = "8fb51db26b49ebe2c3b7992c845f3e7e"
der_zirkus = "0916739a3f9f0c004af563c1629d0477"

# print(
#     create_playlist(
#         "LolYeetus", [bella_maria, der_zirkus], "1741114c47c04c619998619b2ac0ebdf"
#     )
# )
