"""
Load configuration from a JSON file.
Currently only used for WiFi credentials.
"""

import json


class Config:
    def __init__(self, config_file_path: str = "config.json"):
        self.config_file_path = config_file_path
        self.config_data = self.load_config()

    def load_config(self):
        with open(self.config_file_path, "r") as f:
            return json.load(f)

    @property
    def wifi_ssid(self) -> str:
        return self.config_data["wifi"]["ssid"]

    @property
    def wifi_password(self) -> str:
        return self.config_data["wifi"]["password"]
