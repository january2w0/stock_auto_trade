from datetime import datetime

import FinanceDataReader as fdr
import pandas as pd

from backtest.simulator import simulate_trades
from src.strategies.bollinger_bands import BollingerBandsStrategy
from src.strategies.ema_cross import EmaCrossStrategy
from src.strategies.kelly_criterion import KellyCriterionStrategy
from src.strategies.ma_cross import BasicMovingAverageStrategy
from src.strategies.multi_ema_squeeze_kelly import MultiEmaSqueezeKellyStrategy


def get_default_strategies():
    """최적화 시 기본적으로 테스트할 전략 후보군을 반환합니다."""
    return [
        BasicMovingAverageStrategy(short_window=5, long_window=20),
        BollingerBandsStrategy(window=20, k=2),
        EmaCrossStrategy(short_window=5, long_window=20),
        KellyCriterionStrategy(window=20),
        MultiEmaSqueezeKellyStrategy(),
    ]


def optimize_for_symbol(
    ticker: str, days: int = 100, end_date: datetime = None, strategies: list = None
):
    """
    특정 종목에 대해 여러 전략을 테스트하고 가장 최적의 전략 인스턴스를 반환합니다.

    Args:
        ticker (str): 종목 코드 (예: "005930")
        days (int): 테스트할 과거 데이터 일수 (기본값: 100)
        end_date (datetime): 기준일 (기본값: 현재 날짜)
        strategies (list): 테스트할 전략 객체 리스트 (None일 경우 기본 전략 사용)

    Returns:
        Strategy, SimulationResult: 최적의 전략 인스턴스와 해당 전략의 시뮬레이션 결과
    """
    if end_date is None:
        end_date = datetime.now()
    if strategies is None:
        strategies = get_default_strategies()

    date_str = end_date.strftime("%Y-%m-%d")
    print(
        f"\n[{ticker}] {date_str} 기준 과거 {days}일 데이터로 전략 최적화 평가 시작..."
    )

    # 1. 데이터 준비
    try:
        # FinanceDataReader를 사용하여 과거 데이터 가져오기 (pandas-datareader와 유사)
        # 넉넉하게 200일 치를 가져온 후 마지막 days만큼만 사용 (이평선 등 지표 계산 때문)
        start_date = end_date - pd.Timedelta(days=days + 100)

        df = fdr.DataReader(symbol=ticker, start=start_date, end=end_date)
        if df.empty or len(df) < days:
            print(
                f"[{ticker}] 데이터를 충분히 가져오지 못했습니다. 기본 전략으로 폴백합니다."
            )
            return BasicMovingAverageStrategy(), None

    except Exception as e:
        print(f"[{ticker}] 데이터 다운로드 오류: {e}")
        return BasicMovingAverageStrategy(), None

    # 2. 각 전략별 백테스트 실행
    print("-" * 56)
    print(f"{'Strategy':<30} | {'ROI':<10} | {'Win Rate':<10}")
    print("-" * 56)

    best_strategy = None
    best_roi = -float("inf")
    best_result = None

    for strategy in strategies:
        try:
            # 전략에 따른 신호 생성
            df_signals = strategy.generate_signals(df)

            # 지표 계산용 초기 데이터를 뺀 순수 최근 days 구간만 평가
            test_df = df_signals.tail(days)

            # 시뮤레이션
            result = simulate_trades(test_df, initial_balance=1000000)
            roi = result.roi
            win_rate = result.win_rate

            strategy_name = f"{strategy.__class__.__name__}"
            print(f"{strategy_name:<30} | {roi:>9.2f}% | {win_rate:>9.2f}%")

            if roi > best_roi:
                best_roi = roi
                best_strategy = strategy
                best_result = result

        except Exception as e:
            print(f"[{strategy.__class__.__name__}] 평가 중 오류: {e}")

    # 3. 결과 출력
    print("-" * 56)

    if best_strategy:
        print(
            f"🎯 최종 선택 전략: {best_strategy.__class__.__name__} (수익률: {best_roi:.2f}%)"
        )
        return best_strategy, best_result
    else:
        print("적절한 전략을 찾지 못해 기본 전략으로 폴백합니다.")
        return BasicMovingAverageStrategy(), None
