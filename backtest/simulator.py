from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.core.utils import parse_signal


@dataclass
class TradeRecord:
    """개별 매매 기록을 담는 데이터 클래스입니다."""

    date: date
    type: str  # 'BUY' 또는 'SELL'
    price: float
    amount: int
    balance: float


@dataclass
class SimulationResult:
    """백테스트 시뮬레이션 결과를 담는 데이터 클래스입니다."""

    initial_balance: float
    final_value: float
    roi: float
    total_closed_trades: int
    winning_trades: int
    win_rate: float
    trades: list[TradeRecord]
    daily_values: pd.Series = None  # 날짜별 총 자산 가치 (현금 + 주식)


def simulate_trades(
    df: pd.DataFrame, initial_balance: float = 10000000
) -> SimulationResult:
    """
    주어진 데이터프레임과 시그널을 바탕으로 매매를 시뮬레이션합니다.

    Args:
        df (pd.DataFrame): 'Close', 'Signal' 컬럼이 포함된 데이터프레임
        initial_balance (float): 초기 자본

    Returns:
        SimulationResult: 시뮬레이션 결과 데이터 클래스
    """
    balance = initial_balance
    quantity = 0

    trades = []
    buy_price = 0

    winning_trades = 0
    total_closed_trades = 0

    daily_values = {}

    # 첫 날의 자산 가치를 초기 자본금으로 명시적으로 설정
    if not df.empty:
        first_date = df.index[0]
        daily_values[first_date] = initial_balance

    for idx, row in df.iterrows():
        signal = str(row["Signal"])
        price = row["Close"]

        signal_base, fraction = parse_signal(signal)

        # BUY 시그널이고 살 돈이 있을 때 (강도에 따른 분할 매수)
        if "BUY" in signal_base and balance > 0:
            usable_balance = balance * fraction
            amount = int(usable_balance // price)

            if amount > 0:
                # 평단가 (Weighted Average Price) 갱신
                if quantity == 0:
                    buy_price = price
                else:
                    buy_price = ((buy_price * quantity) + (price * amount)) / (
                        quantity + amount
                    )

                quantity += amount
                balance -= amount * price
                trades.append(
                    TradeRecord(
                        date=idx.date(),
                        type="BUY",
                        price=price,
                        amount=amount,
                        balance=balance,
                    )
                )

        # SELL 시그널이고 가진 주식이 있을 때 (강도에 따른 분할 매도)
        elif "SELL" in signal_base and quantity > 0:
            sell_amount = int(quantity * fraction)
            if sell_amount == 0 and quantity > 0:
                sell_amount = quantity  # 극소량일 경우 전량 매도

            sell_revenue = sell_amount * price
            balance += sell_revenue
            quantity -= sell_amount

            # 승률 계산을 위한 기록
            trade_profit = price - buy_price
            if trade_profit > 0:
                winning_trades += 1
            total_closed_trades += 1

            trades.append(
                TradeRecord(
                    date=idx.date(),
                    type="SELL",
                    price=price,
                    amount=sell_amount,
                    balance=balance,
                )
            )
            if quantity == 0:
                buy_price = 0

        # 매일의 총 자산 가치 기록 (현금 + 현재 보유 주식의 가치)
        daily_values[idx] = balance + (quantity * price)

    # 마지막 날 기준으로 보유 주식 가치 평가
    final_value = balance + (quantity * df["Close"].iloc[-1])
    roi = ((final_value / initial_balance) - 1) * 100

    win_rate = 0
    if total_closed_trades > 0:
        win_rate = (winning_trades / total_closed_trades) * 100

    # 일별 자산 가치 시리즈 생성.
    # 첫 날의 값이 중복 덮어씌워지지 않고 자본금 변화가 반영되도록 처리
    dv_series = pd.Series(daily_values)

    return SimulationResult(
        initial_balance=initial_balance,
        final_value=final_value,
        roi=roi,
        total_closed_trades=total_closed_trades,
        winning_trades=winning_trades,
        win_rate=win_rate,
        trades=trades,
        daily_values=dv_series,
    )
