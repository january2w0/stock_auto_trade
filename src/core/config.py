import os

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """프로젝트 전체 설정을 관리하는 클래스"""

    # KIS API 설정
    BASE_URL = os.getenv("BASE_URL", "https://openapivts.koreainvestment.com:29443")
    APPKEY = os.getenv("APPKEY")
    APPSECRET = os.getenv("APPSECRET")
    ACCOUNT = os.getenv("ACCOUNT")


# 싱글톤 인스턴스 생성
config = Config()
