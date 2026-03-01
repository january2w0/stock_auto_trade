import json
import os

import requests

from src.core.config import config

TOKEN_FILE = "kis_token.json"


def get_token():
    """파일에서 토큰을 읽거나, 없으면 새로 발급합니다."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f).get("access_token")
    return issue_token()


def issue_token():
    """토큰을 발급받아 저장하고 반환합니다."""
    url = f"{config.BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": config.APPKEY,
        "appsecret": config.APPSECRET,
    }
    res = requests.post(url, headers={"Content-Type": "application/json"}, json=body)
    token = res.json().get("access_token")
    if token:
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": token}, f)
    return token


if __name__ == "__main__":
    print(f"Issued Token: {issue_token()}")
