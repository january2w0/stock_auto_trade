from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd

from backtest.simulator import simulate_trades
from src.core.strategy_manager import StrategyManager

from .visualization import plot_results

# ==========================================
# ⚙️ 통합 설정
# ==========================================
TARGET_CODES = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "005380",  # 현대자동차
    "035420",  # 네이버
    "382750",  # 당근
    "062040",  # 토스
]
TOTAL_INITIAL_BALANCE = 10_000_000
TEST_DAYS = 365
OPTIMIZE_DAYS = TEST_DAYS // 2


class PortfolioBacktester:
    """
    다중 종목 포트폴리오 백테스트를 수행하는 클래스 (Shifting Time Window 검증)
    """

    def __init__(
        self,
        target_codes: list,
        total_initial_balance: int,
        test_days: int,
        optimize_days: int,
    ):
        self.target_codes = target_codes
        self.total_initial_balance = total_initial_balance
        # 종목당 균등 배분 (계좌 잔고를 종목 수로 나눔)
        self.initial_balance_per_symbol = (
            total_initial_balance / len(target_codes) if target_codes else 0
        )
        self.test_days = test_days
        self.optimize_days = optimize_days

        self.strategy_manager = StrategyManager()

    def _process_symbol(
        self, code: str, test_start_date: datetime, test_end_date: datetime
    ):
        """단일 종목에 대한 시뮬레이션을 격리(Isolate)하여 수행합니다."""
        print(f"\n[{code}] 테스트 구간 시뮬레이션 중...")
        try:
            # 지표 계산(이평선 60일 등)을 위해 넉넉하게 100일 더 가져옴
            start_fetch = test_start_date - timedelta(days=100)
            df = fdr.DataReader(symbol=code, start=start_fetch, end=test_end_date)

            if df.empty:
                print(f"[{code}] 데이터가 부족하여 패스합니다.")
                return None

            strategy = self.strategy_manager.get_strategy(code)
            if not strategy:
                print(f"[{code}] 전략을 가져올 수 없습니다.")
                return None

            df_signals = strategy.generate_signals(df)

            # 실제 거래(테스트)를 진행할 날짜만 자르기 (test_start_date 이후)
            test_df = df_signals.loc[
                df_signals.index >= pd.Timestamp(test_start_date)
            ].copy()

            result = simulate_trades(
                test_df, initial_balance=self.initial_balance_per_symbol
            )

            print(f"[{code}] 적용 전략: {strategy.__class__.__name__}")
            print(
                f"[{code}] 수익률: {result.roi:.2f}% | 승률: {result.win_rate:.2f}% ({result.winning_trades}/{result.total_closed_trades} 시도)"
            )

            return result, test_df

        except Exception as e:
            # 🚨 개별 종목 처리 중 발생한 예외가 전체 시뮬레이션을 다운시키지 못하게 격리(Isolate)
            print(
                f"⚠️ [{code}] 테스트 중 예외 발생 (에러가 격리되어 다음 종목으로 진행): {e}"
            )
            return None

    def run(self):
        """백테스트 메인 루프"""
        print("=" * 60)
        print("다중 종목 백테스트 시작 (Shifting Time Window 검증)")
        print("=" * 60)

        test_end_date = datetime.now()
        test_start_date = test_end_date - timedelta(days=self.test_days)
        optimize_start_date = test_start_date - timedelta(days=self.optimize_days)

        print(
            f"✅ 최적화 기간 (과거 {self.optimize_days}일): {optimize_start_date:%Y-%m-%d} ~ {test_start_date:%Y-%m-%d} 기준"
        )
        print(
            f"✅ 테스트 기간 (최근 {self.test_days}일): {test_start_date:%Y-%m-%d} ~ {test_end_date:%Y-%m-%d} (실전 검증 구간)"
        )

        # 1. 최적화 단계: 백테스트 시작 시점 이전 데이터만 사용 (과적합 방지)
        print("\n--- Phase 1: 통계 기반 전략 최적화 (In-sample) ---")
        self.strategy_manager.optimize_all(
            self.target_codes, days=self.optimize_days, end_date=test_start_date
        )

        # 2. 검증 단계
        print("\n--- Phase 2: 포트폴리오 백테스트 시뮬레이션 (Out-of-sample) ---")
        total_initial_balance = self.total_initial_balance
        total_final_balance = 0
        total_trades_count = 0
        total_winning_trades = 0
        all_daily_values = []
        all_test_dfs = {}

        for code in self.target_codes:
            res = self._process_symbol(code, test_start_date, test_end_date)

            if res:
                result, test_df = res
                total_final_balance += result.final_value
                total_trades_count += result.total_closed_trades
                total_winning_trades += result.winning_trades
                all_daily_values.append(result.daily_values)
                all_test_dfs[code] = test_df
            else:
                total_final_balance += (
                    self.initial_balance_per_symbol
                )  # 오류 나도 원금 유지로 책정
                # 데이터가 없는 경우 원금으로 채워진 Series 생성 (날짜 맞추기 위함)
                # 여기서는 간단히 패스하거나 나중에 합산 시 처리

        # 3. 종합 결과
        print("\n" + "=" * 60)
        print("🌟 다중 종목 포트폴리오 종합 검증 결과 🌟")
        print("-" * 60)
        print(f"테스트 기간 : {test_start_date:%Y-%m-%d} ~ {test_end_date:%Y-%m-%d}")
        print("-" * 60)
        portfolio_roi = ((total_final_balance / total_initial_balance) - 1) * 100
        overall_win_rate = (
            (total_winning_trades / total_trades_count * 100)
            if total_trades_count > 0
            else 0
        )

        print(f"총 초기 자본 : {total_initial_balance:,.0f} 원")
        print(f"총 최종 자본 : {total_final_balance:,.0f} 원")
        print(f"종합 수익률  : {portfolio_roi:.2f}%")
        print(f"총 매매 횟수 : {total_trades_count} 회")
        print(f"종합 승률    : {overall_win_rate:.2f}%")

        # 4. 차트 출력
        if all_daily_values:
            print("\n포트폴리오 자산 그래프를 생성합니다...")
            # 모든 종목의 일자별 가치를 합산
            portfolio_daily_values = pd.concat(all_daily_values, axis=1).sum(axis=1)
            plot_results(
                dfs=all_test_dfs,
                daily_values=portfolio_daily_values,
                title=f"Portfolio Performance ({', '.join(self.target_codes)})",
            )


if __name__ == "__main__":
    backtester = PortfolioBacktester(
        target_codes=TARGET_CODES,
        total_initial_balance=TOTAL_INITIAL_BALANCE,
        test_days=TEST_DAYS,
        optimize_days=OPTIMIZE_DAYS,
    )
    backtester.run()
