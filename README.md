# AutoTrading (한국 주식 자동 매매 봇)

한국투자증권(KIS) API를 활용하여 국내 주식을 자동으로 분석하고 매매하는 파이썬 기반 자동 매매 시스템입니다. 다양한 기술적 지표와 전략 최적화 알고리즘을 통해 효율적인 자산 운용을 목표로 합니다.

## 목차
- [주요 특징](#주요-특징)
- [기술 스택](#기술-스택)
- [사전 준비 사항](#사전-준비-사항)
- [시작하기](#시작하기)
- [아키텍처 개요](#아키텍처-개요)
- [환경 변수 설정](#환경-변수-설정)
- [주요 스크립트](#주요-스크립트)
- [백테스트 및 최적화](#백테스트-및-최적화)
- [문제 해결](#문제-해결)
- [워크 가이드](#워크-가이드)

---

## 주요 특징

- **실시간 시장 모니터링**: 한국 정규 주식 시장(09:00~15:30) 동안 실시간으로 가격을 모니터링하고 시그널을 포착합니다.
- **다양한 매매 전략 지원**:
    - Bollinger Bands (볼린저 밴드)
    - EMA/MA Cross (이평선 교차)
    - Kelly Criterion (켈리 공식 기반 비중 조절)
    - Multi-EMA Squeeze Kelly (복합 전략)
- **전략 자동 최적화**: `StrategyManager`를 통해 주기적으로 과거 데이터를 분석하여 최적의 파라미터를 백그라운드에서 갱신합니다.
- **포트폴리오 백테스팅**: 개별 종목 및 전체 포트폴리오에 대한 백테스트 및 시계열 시각화 기능을 제공합니다.
- **자산 변동 알림**: 총 자산 가치가 특정 비율(예: 10%) 이상 변동할 경우 경고 및 알림을 출력합니다.
- **에러 격리 설계**: 개별 종목 처리 중 에러가 발생해도 전체 시스템이 중단되지 않도록 설계되었습니다.

---

## 기술 스택

- **언어**: Python 3.8+
- **데이터 처리**: Pandas, NumPy
- **API 연동**: Requests (KIS Open API)
- **시각화**: Matplotlib
- **환경 관리**: python-dotenv
- **동시성**: threading (비차단 최적화)

---

## 사전 준비 사항

1. **한국투자증권 계좌**: 실전 계좌 또는 모의투자 계좌가 필요합니다.
2. **API Key 발급**: [한국투자증권 개발자 센터](https://apiportal.koreainvestment.com/)에서 `App Key`와 `App Secret`을 발급받아야 합니다.
3. **Python 설치**: Python 3.8 이상의 환경이 필요합니다.

---

## 시작하기

### 1. 저장소 클론 및 이동
```bash
git clone https://github.com/your-repo/AutoTrading.git
cd AutoTrading
```

### 2. 가상 환경 설정 (권장)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install pandas requests python-dotenv matplotlib
```

### 4. 환경 변수 설정
`.env` 파일을 루트 디렉토리에 생성하고 아래 내용을 입력합니다.
```env
# KIS API 설정
BASE_URL=https://openapivts.koreainvestment.com:29443  # 모의투자 기준
APPKEY=your_app_key_here
APPSECRET=your_app_secret_here
ACCOUNT=your_account_number_here
```

### 5. 매매 봇 실행
```bash
python main.py
```

---

## 아키텍처 개요

### 디렉토리 구조
```
├── backtest/                # 백테스트 및 최적화 엔진
│   ├── simulator.py         # 단일/멀티 시뮬레이터
│   ├── optimizer.py         # 파라미터 최적화 (Grid Search 등)
│   ├── visual_backtest.py   # 시각화 실행 스크립트
│   └── visualization.py     # 차트 생성 유틸리티
├── src/
│   ├── api/                 # KIS API 래퍼
│   │   ├── base_client.py   # 공통 HTTP 클라이언트
│   │   ├── kis_api.py       # 매매/조회 업무 로직
│   │   └── token_manager.py # OAuth2 토큰 관리
│   ├── core/                # 핵심 유틸리티
│   │   ├── config.py        # 설정 로더
│   │   ├── strategy_manager.py # 전략 런타임 관리자
│   │   └── utils.py         # 공통 헬퍼 함수
│   └── strategies/          # 매매 전략 알고리즘
│       ├── base.py          # 전략 추상 클래스
│       └── multi_ema_squeeze_kelly.py # 복합 핵심 전략
├── main.py                  # 실거래 봇 실행 엔트리포인트
└── .env                     # 중요 보안 설정 (Git 제외)
```

### 요청 라이프사이클
1. `main.py` 실행 시 `TradingBot` 인스턴스화
2. `StrategyManager`가 각 종목별 최적 전략 로드
3. 무한 루프 진입:
    - 시장 개장 시간 확인
    - 주기적인 백그라운드 최적화 스케줄링
    - 실시간 현재가 조회 및 전략 시그널 생성
    - 시그널(BUY/SELL) 발생 시 `kis_api`를 통해 주문 실행

---

## 환경 변수 설정

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `BASE_URL` | KIS API 도메인 (실전/모의 구분) | `https://openapi.koreainvestment.com:9443` |
| `APPKEY` | API 앱 키 | `WpX...` |
| `APPSECRET` | API 앱 시크릿 | `XyZ...` |
| `ACCOUNT` | 종합 계좌 번호 (10자리) | `1234567801` |

---

## 주요 스크립트

| 스크립트 | 설명 |
|----------|------|
| `python main.py` | 실제 자동 매매 봇을 실행합니다. |
| `python backtest/visual_backtest.py` | 특정 종목이나 포트폴리오의 백테스트 결과를 차트로 확인합니다. |
| `python src/api/token_manager.py` | 수동으로 API 접근 토큰을 갱신 및 테스트합니다. |

---

## 백테스트 및 최적화

상세한 과거 데이터 분석을 위해 `backtest` 모듈을 사용합니다.

### 백테스트 실행 예시
`backtest/visual_backtest.py` 파일 내에서 대상 종목과 날짜 범위를 수정한 뒤 실행하십시오.
```bash
python backtest/visual_backtest.py
```
- **초록색 선**: 전체 자산 가치 변화 (Normalized)
- **검은색 선**: 종목 가격 변화
- **삼각형 표시**: 매수(빨강) / 매도(파랑) 타점

---

## 문제 해결

### 1. 토큰 만료 에러 (EGW00123)
시스템은 자동으로 토큰을 재발급하도록 설계되어 있습니다. 하지만 지속적으로 발생할 경우 `kis_token.json` 파일을 삭제하고 다시 실행해 보세요.

### 2. 시장가/지정가 주문 관련
현재 기본값은 **지정가(00)** 주문입니다. 시장 상황에 따라 체결되지 않을 수 있으며, 이 경우 1분 뒤 다음 루프에서 기존 주문을 `clear_orders()`로 취소하고 재주문을 시도합니다.

### 3. API 요청 제한
한국투자증권 API는 초당 요청 제한이 있습니다. `time.sleep()`을 통해 적절한 딜레이(예: 0.2초)가 코드 곳곳에 적용되어 있습니다.

---

## 워크 가이드

프로젝트 이해를 돕기 위한 단계별 가이드 문서가 `work-guide/` 디렉토리에 포함되어 있습니다.
- [01. 투자 전략 구현하기](work-guide/01.%20투자%20전략%20구현하기.md)
- [02. 백테스트](work-guide/02.%20백테스트.md)
- [04. 자동 매매 구현하기](work-guide/04.%20자동%20매매%20구현하기.md)
- [05. 실제 주문 연동](work-guide/05.%20실제%20주문%20연동.md)

---

## 라이선스
본 프로젝트는 교육 및 개인 투자 참고용으로 제작되었습니다. 매매로 인한 손실의 책임은 전적으로 사용자에게 있습니다.
