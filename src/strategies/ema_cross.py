import pandas as pd

from .base import Strategy


class EmaCrossStrategy(Strategy):
    """
    지수이동평균(EMA) 크로스 전략입니다.
    단기 EMA가 장기 EMA를 상향 돌파(골든 크로스)하면 매수,
    하향 돌파(데드 크로스)하면 매도합니다.
    """

    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. 지수이동평균(EMA) 계산
        df["EMA_Short"] = df["Close"].ewm(span=self.short_window, adjust=False).mean()
        df["EMA_Long"] = df["Close"].ewm(span=self.long_window, adjust=False).mean()

        # 2. 이동평균 간의 이격도 (Spread) 비율을 측정 (% 기준)
        df["Spread"] = abs(df["EMA_Short"] - df["EMA_Long"]) / df["EMA_Long"]
        df["Strength"] = (df["Spread"] / 0.03).clip(lower=0.1, upper=1.0)

        # 3. 매매 신호 포착 로직 (골든/데드 크로스) 및 format_signal 적용
        df["Signal"] = "HOLD"

        # 골든 크로스 (어제는 Short <= Long, 오늘은 Short > Long)
        golden_cross = (df["EMA_Short"] > df["EMA_Long"]) & (
            df["EMA_Short"].shift(1) <= df["EMA_Long"].shift(1)
        )
        # 데드 크로스 (어제는 Short >= Long, 오늘은 Short < Long)
        dead_cross = (df["EMA_Short"] < df["EMA_Long"]) & (
            df["EMA_Short"].shift(1) >= df["EMA_Long"].shift(1)
        )

        df.loc[golden_cross, "Signal"] = df.loc[golden_cross, "Strength"].apply(
            lambda s: self.format_signal("BUY", s)
        )
        df.loc[dead_cross, "Signal"] = df.loc[dead_cross, "Strength"].apply(
            lambda s: self.format_signal("SELL", s)
        )

        return df

    def get_visual_config(self) -> dict:
        return {
            "plots": [
                {"column": "EMA_Short", "label": "EMA Short", "color": "orange"},
                {"column": "EMA_Long", "label": "EMA Long", "color": "blue"},
            ]
        }
