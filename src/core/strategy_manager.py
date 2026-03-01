import threading
from datetime import datetime

from backtest.optimizer import get_default_strategies, optimize_for_symbol
from src.strategies.base import Strategy


class StrategyManager:
    """
    모든 타겟 종목에 대한 전략의 최적화 상태와 객체를 중앙 집중적으로 관리합니다.
    (스레드 안전성 보장 및 비동기/백그라운드 최적화 기능 포함)
    """

    def __init__(self):
        self.active_strategies: dict[str, Strategy] = {}
        self.last_optimization_date: datetime = None
        self._lock = threading.Lock()
        self.is_optimizing = False

    def get_strategy(self, ticker: str) -> Strategy:
        """
        주어진 종목의 현재 활성화된(최적화된) 최고 효율 전략을 반환합니다.
        (다른 스레드에서 업데이트 중일 때 충돌하지 않도록 Lock을 겁니다)
        """
        with self._lock:
            # 전략이 아예 없으면 일단 기본 껍데기 전략(MA)이라도 던져서 봇 정지를 막음
            return self.active_strategies.get(ticker, get_default_strategies()[0])

    def needs_optimization(self, interval_days: int = 7) -> bool:
        """최후 최적화로부터 지정된 interval_days일 이상 경과했고, 현재 진행 중이 아니라면 True"""
        if self.is_optimizing:
            return False

        if self.last_optimization_date:
            return (datetime.now() - self.last_optimization_date).days >= interval_days

        return True  # 아예 기록이 없으면(최초) 필요함

    def optimize_all(
        self, target_codes: list, days: int = 100, end_date: datetime = None
    ):
        """
        주어진 종목들의 가장 수익률이 좋은 전략을 과거 데이터로 하나씩 찾아서 저장합니다.
        end_date가 지정되면 해당 날짜를 기준으로 과거 데이터를 분석합니다 (백테스트 과적합 방지용).
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{now_str}] 🔄 전략 최적화를 시작합니다. (대상: {target_codes})")

        self.is_optimizing = True
        new_strategies = {}

        try:
            for code in target_codes:
                # optimizer의 로직을 사용하여 최적 도출
                best_strategy, _ = optimize_for_symbol(
                    ticker=code, days=days, end_date=end_date
                )
                new_strategies[code] = best_strategy

            # 백테스트가 다 끝나고 나서 찰나의 순간에만 Lock을 잡고 기존 전략들을 통째로 갈아끼움
            with self._lock:
                self.active_strategies.update(new_strategies)
                self.last_optimization_date = datetime.now()

            print(f"\n[{datetime.now()}] ✅ 전략 최적화가 성공적으로 완료되었습니다.")

        except Exception as e:
            print(f"\n🚨 전략 최적화 중 심각한 오류 발생: {e}")
        finally:
            self.is_optimizing = False

    def optimize_all_async(
        self, target_codes: list, days: int = 100, end_date: datetime = None
    ):
        """
        내부적으로 optimize_all()을 백그라운드 스레드에서 실행시킵니다.
        """
        if self.is_optimizing:
            print("⚠️ 이미 백그라운드 최적화가 진행 중입니다.")
            return

        print("\n🚀 백그라운드 스레드에서 전략 발굴(최적화)을 지시했습니다.")
        thread = threading.Thread(
            target=self.optimize_all, args=(target_codes, days, end_date), daemon=True
        )
        thread.start()
