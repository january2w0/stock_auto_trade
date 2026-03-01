from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd

from backtest.simulator import simulate_trades
from src.core.strategy_manager import StrategyManager
from src.strategies.kelly_criterion import KellyCriterionStrategy

from .visualization import plot_results

# ==========================================
# ⚙️ 통합 설정
# ==========================================
TICKER = "005930"
INITIAL_BALANCE = 10_000_000
TEST_DAYS = 365
OPTIMIZE_DAYS = TEST_DAYS // 2
# 최적화 없이 사용할 기본 전략 (None이면 최적화 수행)
# 예: DEFAULT_STRATEGY = BasicMovingAverageStrategy(short_window=5, long_window=20)
DEFAULT_STRATEGY = KellyCriterionStrategy(window=20)


class VisualBacktester:
    """
    단일 종목에 대한 시각화 포함 백테스트를 수행하는 클래스.
    """

    def __init__(
        self, ticker: str, initial_balance: int, test_days: int, optimize_days: int
    ):
        self.ticker = ticker
        self.initial_balance = initial_balance
        self.test_days = test_days
        self.optimize_days = optimize_days
        self.default_strategy = DEFAULT_STRATEGY

        self.strategy_manager = StrategyManager()

    def run(self):
        """백테스트 메인 루프 및 시각화"""
        test_end_date = datetime.now()
        test_start_date = test_end_date - timedelta(days=self.test_days)

        if self.default_strategy:
            print(
                f"--- 기본 전략 사용 ({self.default_strategy.__class__.__name__}) ---"
            )
            best_strategy = self.default_strategy
        else:
            print(f"--- 전략 최적화 시작 ({self.ticker}) ---")
            # 과적합 방지: 백테스트 시작일 직전 데이터까지만 사용하여 전략 구함 (In-sample)
            self.strategy_manager.optimize_all(
                [self.ticker], days=self.optimize_days, end_date=test_start_date
            )
            best_strategy = self.strategy_manager.get_strategy(self.ticker)

        if not best_strategy:
            print(f"[{self.ticker}] 전략을 가져올 수 없습니다.")
            return

        print(f"\n[{self.ticker}] 백테스트 데이터 다운로드 중...")
        try:
            # 지표 계산을 위해 시작일보다 넉넉하게 100일 더 가져오기
            fetch_start = test_start_date - timedelta(days=100)
            df = fdr.DataReader(
                symbol=self.ticker, start=fetch_start, end=test_end_date
            )

            if df.empty:
                print("데이터가 없습니다.")
                return

            print(f"전략 시그널 생성 중... ({best_strategy.__class__.__name__})")
            df_signals = best_strategy.generate_signals(df)

            # 실제 테스트 기간만 자르기
            test_df = df_signals.loc[
                df_signals.index >= pd.Timestamp(test_start_date)
            ].copy()
            visual_config = best_strategy.get_visual_config()

            print("포트폴리오 시뮬레이션 중...")
            result = simulate_trades(test_df, initial_balance=self.initial_balance)

            print("\n--- 백테스트 결과 ---")
            print(f"기간: {test_df.index[0]:%Y-%m-%d} ~ {test_df.index[-1]:%Y-%m-%d}")
            print(f"초기 자본: {result.initial_balance:,.0f} 원")
            print(f"최종 자본: {result.final_value:,.0f} 원")
            print(f"총 수익률: {result.roi:.2f}%")
            print(f"총 매매 횟수: {result.total_closed_trades}회")
            print(f"승률: {result.win_rate:.2f}%")

            print("\n차트를 생성합니다...")
            plot_results(
                dfs={self.ticker: test_df},
                daily_values=result.daily_values,
                title=f"{self.ticker} Backtest ({best_strategy.__class__.__name__})",
                visual_config=visual_config,
            )

        except Exception as e:
            # 🚨 예외 발생 시 스크립트가 죽지 않고 메시지를 남기도록 격리(Isolate)
            print(f"⚠️ 백테스트 중 일시적 오류 발생: {e}")


if __name__ == "__main__":
    backtester = VisualBacktester(
        ticker=TICKER,
        initial_balance=INITIAL_BALANCE,
        test_days=TEST_DAYS,
        optimize_days=OPTIMIZE_DAYS,
    )
    backtester.run()
