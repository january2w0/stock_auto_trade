import pandas as pd

from .base import Strategy


class BasicMovingAverageStrategy(Strategy):
    """
    기본 이동평균선(MA) 크로스 전략입니다.
    단기 이평선(20일)이 장기 이평선(60일)을 상향 돌파하면 매수,
    하향 돌파하면 매도합니다.
    """

    def __init__(self, short_window=20, long_window=60):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. 이동평균선 계산
        df["MA_Short"] = df["Close"].rolling(window=self.short_window).mean()
        df["MA_Long"] = df["Close"].rolling(window=self.long_window).mean()

        # 2. 이동평균 간의 이격도 (Spread) 비율을 측정 (% 기준)
        df["Spread"] = abs(df["MA_Short"] - df["MA_Long"]) / df["MA_Long"]
        df["Strength"] = (df["Spread"] / 0.03).clip(lower=0.1, upper=1.0)

        # 3. 골든/데드 크로스 판별 및 시그널 생성
        df["Signal"] = "HOLD"

        # 골든 크로스: Short > Long 이면서 어제는 그렇지 않았을 때
        is_buy = (df["MA_Short"] > df["MA_Long"]) & (
            df["MA_Short"].shift(1) <= df["MA_Long"].shift(1)
        )
        # 데드 크로스: Short < Long 이면서 어제는 그렇지 않았을 때
        is_sell = (df["MA_Short"] < df["MA_Long"]) & (
            df["MA_Short"].shift(1) >= df["MA_Long"].shift(1)
        )

        df.loc[is_buy, "Signal"] = df.loc[is_buy, "Strength"].apply(
            lambda s: self.format_signal("BUY", s)
        )
        df.loc[is_sell, "Signal"] = df.loc[is_sell, "Strength"].apply(
            lambda s: self.format_signal("SELL", s)
        )

        return df

    def get_visual_config(self) -> dict:
        return {
            "plots": [
                {"column": "MA_Short", "label": "MA Short", "color": "orange"},
                {"column": "MA_Long", "label": "MA Long", "color": "blue"},
            ]
        }
