import numpy as np
import pandas as pd

from .base import Strategy


class KellyCriterionStrategy(Strategy):
    """
    켈리 공식(Kelly Criterion) 비중 조절 전략입니다.
    과거 n일의 승률과 손익비를 바탕으로 투자 비중을 결정합니다.
    비중이 0보다 크면 매수(비중 조절), 0 이하면 매도(현금화)합니다.
    """

    def __init__(self, window=60):
        self.window = window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. 켈리 공식 비중 계산
        df["Return"] = df["Close"].pct_change()
        df["Win"] = (df["Return"] > 0).astype(int)
        df["W"] = df["Win"].rolling(window=self.window).mean()

        df["Gain"] = np.where(df["Return"] > 0, df["Return"], 0)
        df["Loss"] = np.where(df["Return"] < 0, abs(df["Return"]), 0)

        avg_gain = pd.Series(df["Gain"]).rolling(window=self.window).mean()
        avg_loss = pd.Series(df["Loss"]).rolling(window=self.window).mean()

        # 손실이 0일 경우 0으로 나누는 오류 방지
        df["R"] = np.where(avg_loss == 0, 0, avg_gain / avg_loss)

        # 켈리 비중(f*) = W - ((1 - W) / R)
        df["Kelly_Fraction"] = df["W"] - ((1 - df["W"]) / df["R"])
        df["Kelly_Fraction"] = np.clip(df["Kelly_Fraction"], 0, 1)

        # 2. 매매 신호 포착
        def get_signal(row):
            if pd.isna(row["Kelly_Fraction"]):
                return "HOLD"
            if row["Kelly_Fraction"] > 0:
                # 켈리 비중을 포함한 BUY 시그널 전송
                return self.format_signal("BUY", row["Kelly_Fraction"])
            else:
                # 켈리 비중이 0 이하면 전량 매도
                return self.format_signal("SELL", 1.0)

        df["Signal"] = df.apply(get_signal, axis=1)

        return df

    def get_visual_config(self) -> dict:
        """켈리 비중(0~1)을 차트에 표시합니다."""
        return {
            "plots": [
                {
                    "column": "Kelly_Fraction",
                    "label": "Kelly Weight",
                    "color": "orange",
                    "linestyle": "--",
                    "normalize": False,  # 0~1 비율값이므로 가격 스케일 정규화 제외
                }
            ]
        }
