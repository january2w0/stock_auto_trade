import requests

from src.api import token_manager
from src.core.config import config


class KISClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or config.BASE_URL

    @staticmethod
    def _get_headers(tr_id=None, include_auth=True):
        """API 요청에 필요한 공통 헤더를 생성합니다."""
        headers = {
            "Content-Type": "application/json",
            "appkey": config.APPKEY,
            "appsecret": config.APPSECRET,
        }
        if tr_id:
            headers["tr_id"] = tr_id
        if include_auth:
            headers["authorization"] = f"Bearer {token_manager.get_token()}"
        return headers

    def request(
        self, method, path, tr_id=None, params=None, json=None, include_auth=True
    ):
        url = f"{self.base_url}{path}"
        headers = self._get_headers(tr_id, include_auth)

        res = requests.request(method, url, headers=headers, params=params, json=json)
        data = res.json()

        # 토큰 만료 에러 발생 시 자동 재발급 후 1회 재시도
        if include_auth and data.get("msg_cd") == "EGW00123":
            print("Token expired. Re-issuing...")
            headers["authorization"] = f"Bearer {token_manager.issue_token()}"
            res = requests.request(
                method, url, headers=headers, params=params, json=json
            )
            data = res.json()

        return data


kis_client = KISClient()
