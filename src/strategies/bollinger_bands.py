import pandas as pd

from .base import Strategy


class BollingerBandsStrategy(Strategy):
    """
    볼린저 밴드(Bollinger Bands) 전략입니다.
    종가가 하단선을 이탈하면 매수(과매도),
    상단선을 돌파하면 매도(과매수)합니다.
    """

    def __init__(self, window=20, k=2):
        self.window = window
        self.k = k

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. 볼린저 밴드 계산
        df["SMA"] = df["Close"].rolling(window=self.window).mean()
        df["STD"] = df["Close"].rolling(window=self.window).std()
        df["Upper"] = df["SMA"] + (df["STD"] * self.k)
        df["Lower"] = df["SMA"] - (df["STD"] * self.k)

        # 2. 매매 신호 포착 로직 (Pandas 벡터화 연산 사용)
        df["Bandwidth"] = df["Upper"] - df["Lower"]

        # 기본 시그널은 HOLD
        df["Signal"] = "HOLD"

        # 안전한 계산을 위해 유효한 데이터만 필터링
        valid_mask = pd.notna(df["Upper"]) & (df["Bandwidth"] > 0)

        # 매수/매도 조건 마스킹
        is_buy = valid_mask & (df["Close"] < df["Lower"])
        is_sell = valid_mask & (df["Close"] > df["Upper"])

        # 조건에 맞는 행에 대해서만 강도 계산 및 신호 포맷팅 적용
        if is_buy.any():
            buy_distance_ratio = (
                df.loc[is_buy, "Lower"] - df.loc[is_buy, "Close"]
            ) / df.loc[is_buy, "Bandwidth"]
            df.loc[is_buy, "Signal"] = (buy_distance_ratio / 0.5).apply(
                lambda s: self.format_signal("BUY", s)
            )

        if is_sell.any():
            sell_distance_ratio = (
                df.loc[is_sell, "Close"] - df.loc[is_sell, "Upper"]
            ) / df.loc[is_sell, "Bandwidth"]
            df.loc[is_sell, "Signal"] = (sell_distance_ratio / 0.5).apply(
                lambda s: self.format_signal("SELL", s)
            )

        return df

    def get_visual_config(self) -> dict:
        return {
            "plots": [
                {
                    "column": "Upper",
                    "label": "Upper Band",
                    "color": "gray",
                    "linestyle": "--",
                },
                {"column": "SMA", "label": "SMA", "color": "orange", "linestyle": "-"},
                {
                    "column": "Lower",
                    "label": "Lower Band",
                    "color": "gray",
                    "linestyle": "--",
                },
            ]
        }
