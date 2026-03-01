import numpy as np
import pandas as pd

from .base import Strategy


class MultiEmaSqueezeKellyStrategy(Strategy):
    """
    다중 지수이동평균선(EMA Ribbon)의 수축과 특정 EMA 크로스오버,
    그리고 켈리 공식을 결합한 고도화된 전략입니다.
    """

    def __init__(
        self,
        ema_windows=(5, 10, 15, 20, 25, 30),  # 변동성(수축) 파악을 위한 다중 EMA 기간
        cross_short=5,  # 타이밍 포착용 단기 EMA
        cross_long=20,  # 타이밍 포착용 장기 EMA
        squeeze_threshold=0.4,  # RSI 스타일 이격 지수 임계치 (0.3 이하일 때 수축으로 판단)
        kelly_window=60,  # 켈리 공식 계산을 위한 과거 기간
        squeeze_window=14,  # 이격 지수(RSI 스타일) 계산을 위한 기간
    ):
        self.ema_windows = ema_windows
        self.cross_short = cross_short
        self.cross_long = cross_long
        self.squeeze_threshold = squeeze_threshold
        self.kelly_window = kelly_window
        self.squeeze_window = squeeze_window

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ----------------------------------------------------------------
        # 1. 다중 EMA 계산 및 변동성 수축(Squeeze) 파악
        # ----------------------------------------------------------------
        ema_cols = []
        for w in self.ema_windows:
            col_name = f"EMA_{w}"
            df[col_name] = df["Close"].ewm(span=w, adjust=False).mean()
            ema_cols.append(col_name)

        # 다중 EMA 집합의 최댓값, 최솟값, 평균 도출
        df["EMA_Max"] = df[ema_cols].max(axis=1)
        df["EMA_Min"] = df[ema_cols].min(axis=1)
        df["EMA_Mean"] = df[ema_cols].mean(axis=1)

        # 1-1. 기초 이격도 계산: (최댓값 - 최솟값) / 평균
        raw_spread = (df["EMA_Max"] - df["EMA_Min"]) / df["EMA_Mean"]

        # 1-2. RSI 스타일의 이격 지수 (Relative Spread Index) 계산
        # 이격의 확장(Gain)과 수축(Loss)의 상대적 강도를 비교합니다.
        delta = raw_spread.diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, abs(delta), 0)

        avg_gain = pd.Series(gain).rolling(window=self.squeeze_window).mean()
        avg_loss = pd.Series(loss).rolling(window=self.squeeze_window).mean()

        # Ribbon_Spread = RSI-like index (0~1 범위)
        # 0에 가까울수록 수축(Squeeze) 경향이 강하고, 1에 가까울수록 확장(Trend) 경향이 강함
        denominator = avg_gain + avg_loss
        df["Ribbon_Spread"] = np.where(denominator > 0, avg_gain / denominator, 0.5)

        # 현재 이격 지수가 임계치 이하인지 판단 (수축이 지배적일 때)
        df["Is_Squeeze"] = df["Ribbon_Spread"] <= self.squeeze_threshold

        # 크로스오버가 일어날 때는 일시적으로 간격이 벌어질 수 있으므로,
        # 직전 3일 내에 한 번이라도 선들이 밀집(Squeeze)했었는지 확인
        df["Recent_Squeeze"] = (
            df["Is_Squeeze"].rolling(window=3).max().fillna(0).astype(bool)
        )

        # ----------------------------------------------------------------
        # 2. 켈리 공식 비중(Kelly Fraction) 계산
        # ----------------------------------------------------------------
        df["Return"] = df["Close"].pct_change()
        df["Win"] = (df["Return"] > 0).astype(int)
        df["W"] = df["Win"].rolling(window=self.kelly_window).mean()

        df["Gain"] = np.where(df["Return"] > 0, df["Return"], 0)
        df["Loss"] = np.where(df["Return"] < 0, abs(df["Return"]), 0)

        avg_gain = pd.Series(df["Gain"]).rolling(window=self.kelly_window).mean()
        avg_loss = pd.Series(df["Loss"]).rolling(window=self.kelly_window).mean()

        df["R"] = np.where(avg_loss == 0, 0, avg_gain / avg_loss)

        # f* = W - ((1 - W) / R)
        df["Kelly_Fraction"] = df["W"] - ((1 - df["W"]) / df["R"])
        df["Kelly_Fraction"] = np.clip(df["Kelly_Fraction"], 0, 1)

        # ----------------------------------------------------------------
        # 3. 매매 타이밍 포착 (특정 EMA 크로스오버 + Squeeze 필터)
        # ----------------------------------------------------------------
        df["Signal"] = "HOLD"

        # 타이밍용 EMA 설정 (이미 계산되었다면 재사용 가능하지만, 유연성을 위해 분리)
        df["Cross_Short"] = df["Close"].ewm(span=self.cross_short, adjust=False).mean()
        df["Cross_Long"] = df["Close"].ewm(span=self.cross_long, adjust=False).mean()

        # 골든 크로스 / 데드 크로스
        golden_cross = (df["Cross_Short"] > df["Cross_Long"]) & (
            df["Cross_Short"].shift(1) <= df["Cross_Long"].shift(1)
        )
        dead_cross = (df["Cross_Short"] < df["Cross_Long"]) & (
            df["Cross_Short"].shift(1) >= df["Cross_Long"].shift(1)
        )

        # 직전에 변동성이 수축된 상태에서 크로스오버가 발생했는지 확인
        valid_buy = golden_cross & df["Recent_Squeeze"].shift(1)
        # 매도는 수축과 상관없이 데드 크로스 발생 시 즉시 실행
        valid_sell = dead_cross

        # 매수: 켈리 비중이 양수일 때만 해당 비중으로 BUY
        df.loc[valid_buy, "Signal"] = df.loc[valid_buy, "Kelly_Fraction"].apply(
            lambda k: self.format_signal("BUY", k) if k > 0 else "HOLD"
        )

        # 매도: 조건 충족 시 비중 1.0(전량)으로 SELL
        df.loc[valid_sell, "Signal"] = df.loc[valid_sell, "Kelly_Fraction"].apply(
            lambda k: self.format_signal("SELL", 1.0)
        )

        return df

    def get_visual_config(self) -> dict:
        """차트에 다중 EMA 리본과 켈리 비중을 시각적으로 표시합니다."""
        plots = []

        # 1. 다중 EMA 리본 추가 (투명한 색상톤이나 얇은 선으로 통일하면 예쁩니다)
        for w in self.ema_windows:
            plots.append(
                {
                    "column": f"EMA_{w}",
                    "label": f"EMA {w}",
                    "linestyle": "-",
                    "alpha": 0.4,
                    "normalize": True,
                }
            )

        # 2. 크로스오버의 주축이 되는 EMA 추가
        plots.append(
            {
                "column": "Cross_Short",
                "label": f"Cross Short({self.cross_short})",
                "color": "red",
                "linewidth": 2,
                "normalize": True,
            }
        )
        plots.append(
            {
                "column": "Cross_Long",
                "label": f"Cross Long({self.cross_long})",
                "color": "blue",
                "linewidth": 2,
                "normalize": True,
            }
        )

        # 3. 켈리 비중 (보조지표, 0~1 사이의 값이므로 normalize=False)
        plots.append(
            {
                "column": "Kelly_Fraction",
                "label": "Kelly Weight",
                "color": "purple",
                "linestyle": "--",
                "normalize": False,
            }
        )

        # 4. EMA 이격 지수 (Ribbon Spread RSI, 0~1 사이의 값이므로 normalize=False)
        plots.append(
            {
                "column": "Ribbon_Spread",
                "label": "EMA Spread RSI",
                "color": "darkcyan",
                "linestyle": ":",
                "normalize": False,
            }
        )

        return {"plots": plots}
