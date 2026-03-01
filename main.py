import time
from collections import deque
from datetime import datetime
from datetime import time as dt_time

import pandas as pd

from backtest.simulator import parse_signal
from src.api import kis_api as api
from src.core.config import config
from src.core.strategy_manager import StrategyManager

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
ACCOUNT = config.ACCOUNT
OPTIMIZATION_INTERVAL_DAYS = 7


class TradingBot:
    """
    포트폴리오 구성 종목에 대해 주기적으로 전략을 최적화하고 매매를 수행하는 봇 클래스.
    """

    def __init__(
        self, target_codes: list, account: str, optimization_interval_days: int
    ):
        self.target_codes = target_codes
        self.account = account
        self.optimization_interval_days = optimization_interval_days

        self.strategy_manager = StrategyManager()
        self.price_history = {code: deque(maxlen=300) for code in self.target_codes}
        self.last_notified_eval = None

    def _execute_trade(
        self,
        code: str,
        action: str,
        fraction: float,
        current_price: int,
        allocated_budget: int,
    ):
        """계좌 상태를 파악한 뒤 실제로 매수 또는 매도 API를 호출합니다."""
        current_qty = api.fetch_quantity(self.account, code)

        if action == "BUY":
            # 목표 보유 수량 산정 후 현재 보유 수량 차감 (잔여 매수 여력 확인)
            target_amount = allocated_budget // current_price
            buy_amount = int((target_amount - current_qty) * fraction)
            if buy_amount <= 0:
                return

            # 예수금(증거금) 초과 방지 2차 확인
            avail_qty = api.fetch_avail(self.account, code, current_price)
            final_buy_amount = min(buy_amount, avail_qty)
            if final_buy_amount <= 0:
                return

            api.order("BUY", self.account, code, final_buy_amount, current_price)
            print(
                f"BUY: {code} {final_buy_amount}ea @ {current_price:,} ({fraction * 100:.0f}%)"
            )

        elif action == "SELL":
            sell_amount = int(current_qty * fraction)

            # 비중 적용 계산 시 0주로 떨어지지만 잔여물량이 있다면 전량 매도로 보정 (먼지방지)
            if sell_amount == 0 and current_qty > 0:
                sell_amount = current_qty

            if sell_amount <= 0:
                return

            api.order("SELL", self.account, code, sell_amount, current_price)
            print(
                f"SELL: {code} {sell_amount}ea @ {current_price:,} ({fraction * 100:.0f}%)"
            )

    def _process_symbol(self, code: str, current_time: datetime, allocated_budget: int):
        """단일 종목에 대한 가격 조회 -> 시그널 판독 -> 주문 체결 로직의 1사이클을 수행합니다."""
        try:
            current_price = api.fetch_current_price(code)
            if current_price is None:
                return

            # 데이터 누적 (deque 속성에 의해 자동으로 최근 300개의 데이터만 유지됨)
            self.price_history[code].append(
                {"Date": current_time, "Close": current_price}
            )

            df = pd.DataFrame(self.price_history[code]).set_index("Date")

            # 🛠 안전하게 전략 꺼내오기 (Lock 적용됨)
            strategy = self.strategy_manager.get_strategy(code)
            if not strategy:
                return

            # 전략 시그널 포착 및 파싱
            df_with_signals = strategy.generate_signals(df)
            latest_signal = df_with_signals["Signal"].iloc[-1]
            action, fraction = parse_signal(latest_signal)

            print(
                f"[{current_time:%H:%M:%S}] {code}: {current_price:,} | {latest_signal} | {strategy.__class__.__name__}"
            )

            # 불필요한 API 통신 절약을 위한 Early Return
            if action == "HOLD":
                return

            # 과거 미체결 주문 취소
            api.clear_orders(self.account, code)

            # 실 거래 집행
            self._execute_trade(code, action, fraction, current_price, allocated_budget)

        except Exception as e:
            # 🚨 개별 종목 처리 중 발생한 예외가 전체 봇을 다운시키지 못하게 격리(Isolate)
            print(
                f"⚠️ [{code}] 종목 처리 중 일시적인 오류 발생 (다음 종목은 진행됨): {e}"
            )

    def _is_market_open(self):
        """현재 시간이 한국 정규 주식 시장 거래 시간(평일 09:00~15:30)인지 확인합니다."""
        now = datetime.now()
        # 주말 확인 (5: 토요일, 6: 일요일)
        if now.weekday() >= 5:
            return False

        # 정규 거래 시간 확인 (09:00 ~ 15:30)
        return dt_time(9, 0) <= now.time() <= dt_time(15, 30)

    def _monitor_asset_variation(self, eval_amt: int):
        """총 자산 가치의 변동폭을 감시하여 +-10% 이상 변동 시 알림을 출력합니다."""
        if self.last_notified_eval is None:
            self.last_notified_eval = eval_amt
            return

        change_rate = (eval_amt - self.last_notified_eval) / self.last_notified_eval
        if abs(change_rate) >= 0.1:
            direction = "🚀 상승" if change_rate > 0 else "⚠️ 하락"
            print(f"\n[🔔 자산 변동 알림] {direction} {change_rate * 100:+.2f}% 발생!")
            print(f"이전: {self.last_notified_eval:,.0f} -> 현재: {eval_amt:,.0f}\n")
            self.last_notified_eval = eval_amt

    def run(self):
        """봇의 메인 루프. 무한 반복하며 정해진 주기마다 작업을 수행합니다."""
        print(f"\n[{datetime.now()}] 🚀 Bot v2 시작: {self.target_codes}")

        # 1. 봇 시작 시 최초 1회 동기식 최적화 세팅 (블로킹 보장)
        print("--- 초기 최적화 대기 중... ---")
        self.strategy_manager.optimize_all(self.target_codes, days=100)

        while True:
            try:
                current_time = datetime.now()

                # 시장 운영 시간 외에는 대기
                if not self._is_market_open():
                    print(
                        f"[{current_time:%H:%M:%S}] 😴 현재 시장 휴장 중입니다. (평일 09:00~15:30 운영)"
                    )
                    time.sleep(1800)  # 30분 대기
                    continue

                # 2. 백그라운드 재최적화 스케줄 점검 (스레드 분기, 논블로킹 상태로 속행)
                if self.strategy_manager.needs_optimization(
                    self.optimization_interval_days
                ):
                    self.strategy_manager.optimize_all_async(
                        self.target_codes, days=100
                    )

                # 3. 예산 계산 (균등 분배)
                eval_amt = api.fetch_eval(self.account)
                if eval_amt is None:
                    print("자산 조회 실패, 3초 뒤 재시도...")
                    time.sleep(3)
                    continue

                # 💡 자산 가치 변동 모니터링 (+-10% 발생 시 출력)
                self._monitor_asset_variation(eval_amt)

                allocated_budget_per_symbol = eval_amt // len(self.target_codes)
                print(
                    f"💰 자산: {eval_amt:,.0f} (종목당: {allocated_budget_per_symbol:,.0f})"
                )

                # 4. 종목별 로직 독립 수행 (에러 격리 설계)
                for code in self.target_codes:
                    self._process_symbol(
                        code, current_time, allocated_budget_per_symbol
                    )

            except KeyboardInterrupt:
                # 사용자가 수동으로 스크립트 강제 종료 (Ctrl+C)
                print("\n🛑 봇이 중단되었습니다.")
                break

            except Exception as e:
                print(f"🚨 메인 루프 에러 발생, 1분 뒤 재개합니다: {e}")

            # 1분(60초) 대기 후 다음 가격 모니터링
            time.sleep(60)


if __name__ == "__main__":
    bot = TradingBot(
        target_codes=TARGET_CODES,
        account=ACCOUNT,
        optimization_interval_days=OPTIMIZATION_INTERVAL_DAYS,
    )
    bot.run()
