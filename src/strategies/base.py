from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """
    모든 투자 전략의 기본이 되는 추상 클래스입니다.
    """

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        주어진 가격 데이터(DataFrame)에 전략 계산 및 매매 시그널을 추가하여 반환합니다.

        Args:
            df (pd.DataFrame): 최소한 'Close' (종가) 컬럼을 포함하는 과거 데이터프레임.
                               'Open', 'High', 'Low', 'Volume' 등 포함 가능.

        Returns:
            pd.DataFrame: 전략 계산에 필요한 내부 컬럼(예: 이평선, 밴드값 등)과
                          'Signal' 컬럼(예: 'Buy (진입)', 'Sell (청산)', 'Hold (관망)' 등)이
                          추가된 데이터프레임.
        """
        pass

    def get_visual_config(self) -> dict:
        """
        전략별 시각화 설정을 반환합니다.
        기본적으로는 빈 설정을 반환하며, 하위 클래스에서 오버라이드하여
        차트에 표시할 지표(Indicator) 등을 정의합니다.
        """
        return {}

    def format_signal(self, action: str, strength: float = 1.0) -> str:
        """
        매매 액션과 강도를 결합한 표준 시그널 문자열을 생성합니다.
        
        Args:
            action (str): 'BUY', 'SELL', 'HOLD' 중 하나.
            strength (float): 매매 강도 (0.1 ~ 1.0). 기본값 1.0.
            
        Returns:
            str: 'BUY_0.50', 'SELL_1.00', 'HOLD' 등의 형식.
        """
        if action not in ["BUY", "SELL"]:
            return "HOLD"
        
        # 강도를 0.1 ~ 1.0 사이로 클리핑
        clamped_strength = max(0.1, min(1.0, strength))
        return f"{action}_{clamped_strength:.2f}"
