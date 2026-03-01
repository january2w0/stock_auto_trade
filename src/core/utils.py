def parse_signal(signal_str: str):
    """'BUY_0.5' 형태의 시그널을 로직(action)과 비중(fraction) 튜플로 분리 반환합니다."""
    signal_str = str(signal_str)

    if "_" in signal_str:
        parts = signal_str.split("_")
        action = parts[0]
        try:
            fraction = float(parts[1])
        except (ValueError, IndexError):
            fraction = 1.0
    else:
        action = signal_str
        fraction = 1.0

    return action, fraction
