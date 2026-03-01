from datetime import datetime

from src.api.base_client import kis_client

# 공통 API 경로 상수
DOMESTIC_QUOTATION_BASE = "/uapi/domestic-stock/v1/quotations"
DOMESTIC_TRADING_BASE = "/uapi/domestic-stock/v1/trading"

# TR ID 상수
TR_ID = {
    "PRICE": "FHKST01010100",   # 주식현재가 시세
    "BALANCE": "VTTC8434R",     # 주식잔고조회
    "ORDER_LIST": "VTTC8001R",  # 주식일별주문체결조회
    "CANCEL": "VTTC0803U",      # 주식주문취소
    "ORDER_PSBL": "VTTC8908R",  # 주식주문가능조회
    "BUY": "VTTC0802U",         # 주식현금매수주문
    "SELL": "VTTC0801U",        # 주식현금매도주문
}


def _parse_int(value, default=0):
    """문자열 숫자를 정수로 안전하게 변환합니다."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _base_params(account):
    """지정된 계좌 번호에서 CANO와 ACNT_PRDT_CD를 추출하여 반환합니다."""
    return {
        "CANO": account[:8],
        "ACNT_PRDT_CD": account[-2:],
    }


def _fetch_balance(account):
    """주식 잔고 원본 데이터를 가져옵니다."""
    path = f"{DOMESTIC_TRADING_BASE}/inquire-balance"
    params = {
        **_base_params(account),
        "AFHR_FLPR_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "00",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    return kis_client.request("GET", path, tr_id=TR_ID["BALANCE"], params=params)


def fetch_current_price(code):
    """주식현재가 정보를 가져옵니다."""
    path = f"{DOMESTIC_QUOTATION_BASE}/inquire-price"
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}

    data = kis_client.request("GET", path, tr_id=TR_ID["PRICE"], params=params)
    quotation = data.get("output", {})

    if quotation:
        return _parse_int(quotation.get("stck_prpr"), default=None)
    return None


def fetch_orders(account, code):
    """오늘의 미체결 주문 목록을 가져옵니다."""
    today = datetime.today().strftime("%Y%m%d")
    path = f"{DOMESTIC_TRADING_BASE}/inquire-daily-ccld"
    params = {
        **_base_params(account),
        "INQR_STRT_DT": today,
        "INQR_END_DT": today,
        "SLL_BUY_DVSN_CD": "00",
        "INQR_DVSN": "00",
        "PDNO": code,
        "CCLD_DVSN": "02",
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    data = kis_client.request("GET", path, tr_id=TR_ID["ORDER_LIST"], params=params)
    orders = data.get("output1", [])

    if orders:
        return orders
    return []


def cancel_order(account, order_no):
    """특정 주문 번호의 주문을 취소합니다."""
    path = f"{DOMESTIC_TRADING_BASE}/order-rvsecncl"
    body = {
        **_base_params(account),
        "KRX_FWDG_ORD_ORGNO": "",
        "ORGN_ODNO": order_no,
        "ORD_DVSN": "00",
        "RVSE_CNCL_DVSN_CD": "02",
        "ORD_QTY": "0",
        "ORD_UNPR": "0",
        "QTY_ALL_ORD_YN": "Y",
    }

    data = kis_client.request("POST", path, tr_id=TR_ID["CANCEL"], json=body)

    if data:
        return data.get("rt_cd") == "0"
    return False


def clear_orders(account, code):
    """특정 종목의 모든 미체결 주문을 일괄 취소합니다."""
    for order_info in fetch_orders(account, code):
        if odno := order_info.get("odno"):
            success = cancel_order(account, odno)
            print(f"{odno} 취소 {'성공' if success else '실패'}")


def fetch_avail(account, code, target_price):
    """매수 가능 수량을 조회합니다."""
    path = f"{DOMESTIC_TRADING_BASE}/inquire-psbl-order"
    params = {
        **_base_params(account),
        "PDNO": code,
        "ORD_UNPR": str(target_price),
        "ORD_DVSN": "00",
        "CMA_EVLU_AMT_ICLD_YN": "N",
        "OVRS_ICLD_YN": "N",
    }

    data = kis_client.request("GET", path, tr_id=TR_ID["ORDER_PSBL"], params=params)
    psbl_info = data.get("output", {})

    if psbl_info:
        return _parse_int(psbl_info.get("nrcvb_buy_qty"), default=0)
    return 0


def fetch_quantity(account, code):
    """현재 보유 수량을 조회합니다."""
    data = _fetch_balance(account)
    holdings = data.get("output1", [])
    match = next((item for item in holdings if item.get("pdno") == code), None)

    if match:
        return _parse_int(match.get("hldg_qty"), default=0)
    return 0


def order(order_type, account, code, amount, target_price):
    """매수 혹은 매도 주문을 전송합니다."""
    path = f"{DOMESTIC_TRADING_BASE}/order-cash"
    tr_id = TR_ID["BUY"] if order_type == "BUY" else TR_ID["SELL"]
    body = {
        **_base_params(account),
        "PDNO": code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(amount),
        "ORD_UNPR": str(target_price),
    }

    data = kis_client.request("POST", path, tr_id=tr_id, json=body)

    if data:
        return data.get("rt_cd") == "0"
    return False


def fetch_eval(account):
    """총 평가 금액을 조회합니다."""
    data = _fetch_balance(account)
    summary = data.get("output2", [])

    if summary:
        return _parse_int(summary[0].get("tot_evlu_amt"), default=None)
    return None
