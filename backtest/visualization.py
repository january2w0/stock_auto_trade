import matplotlib.pyplot as plt
import pandas as pd


def plot_results(
    dfs: dict[str, pd.DataFrame] | pd.DataFrame,
    daily_values: pd.Series,
    title: str = "Backtest Result",
    visual_config: dict = None,
):
    """
    단일 종목 및 포트폴리오의 백테스트 결과를 시각화합니다.
    종목 가격 및 지표는 왼쪽 축에 투명도(alpha) 0.5로,
    자산 가치 그래프는 같은 축에 투명도 1.0으로 표시됩니다 (스케일 동기화).
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # 1. 입력 정규화 (딕셔너리 형태)
    if isinstance(dfs, pd.DataFrame):
        dfs = {"Close": dfs}

    is_multi = len(dfs) > 1
    colors = plt.cm.tab10.colors

    # 2. 각 종목별 데이터 플로팅 (가격, 시그널, 라벨)
    for i, (name, df) in enumerate(dfs.items()):
        color = colors[i % len(colors)] if is_multi else "black"
        _plot_symbol_data(ax, name, df, color, is_multi, is_first=(i == 0))

    # 3. 추가 지표 오버레이 (단일 종목일 때만 수행)
    if not is_multi and visual_config and "plots" in visual_config:
        _plot_indicators(ax, list(dfs.values())[0], visual_config["plots"])

    # 4. 전체 자산 가치 그래프
    if daily_values is not None:
        _plot_asset_line(ax, daily_values)

    # 5. 차트 서식 설정
    ax.set_ylabel("Price / Indicator (Ratio)", fontsize=12)
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.set_title(title, fontsize=16)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left")

    plt.tight_layout()
    plt.show()


def _plot_symbol_data(ax, name, df, color, is_multi, is_first):
    """개별 종목의 가격 선, 매매 시그널, 시작/현재가 라벨을 그립니다."""
    scale = df["Close"].iloc[0]
    normalized = df["Close"] / scale
    label = f"{name} Price (Ratio)" if name != "Close" else "Close Price (Ratio)"

    # 가격 곡선
    ax.plot(df.index, normalized, label=label, color=color, alpha=0.5, linewidth=1.5)

    # 시작 및 현재 가격 텍스트 (ratio (actual_price))
    _add_price_texts(ax, df, normalized, scale, color)

    # 매매 시그널
    if "Signal" in df.columns:
        _plot_trading_signals(ax, df, scale, is_multi, is_first)


def _add_price_texts(ax, df, normalized, scale, color):
    """그래프의 시작점과 끝점에 가격 정보를 추가합니다."""
    # 시작가
    ax.text(
        df.index[0],
        1.0,
        f"1.0 ({scale:,.0f})",
        fontsize=8,
        color=color,
        alpha=0.8,
        verticalalignment="bottom",
        horizontalalignment="right",
    )
    # 현재가
    curr_val = normalized.iloc[-1]
    curr_price = df["Close"].iloc[-1]
    ax.text(
        df.index[-1],
        curr_val,
        f"{curr_val:.2f} ({curr_price:,.0f})",
        fontsize=8,
        color=color,
        alpha=0.8,
        verticalalignment="bottom",
        horizontalalignment="right",
    )


def _plot_trading_signals(ax, df, scale, is_multi, is_first):
    """BUY/SELL 시그널을 산점도로 표시합니다."""
    signal_styles = [("BUY", "^", "red"), ("SELL", "v", "blue")]

    for sig_type, marker, color in signal_styles:
        signals = df[df["Signal"].str.contains(sig_type, na=False)]
        if not signals.empty:
            ax.scatter(
                signals.index,
                signals["Close"] / scale,
                marker=marker,
                color=color,
                label=f"{sig_type} Signal" if is_first else None,
                s=80 if not is_multi else 40,
                alpha=0.5,
                zorder=5,
            )


def _plot_indicators(ax, df, plots_cfg):
    """보조 지표(이평선 등)를 정규화하거나 그대로 오버레이합니다."""
    scale = df["Close"].iloc[0]
    for cfg in plots_cfg:
        col = cfg.get("column")
        if col in df.columns:
            # 기본적으로 정규화(True) 수행, 명시적으로 False일 때만 원본값 사용
            should_normalize = cfg.get("normalize", True)
            plot_val = df[col] / scale if should_normalize else df[col]

            ax.plot(
                df.index,
                plot_val,
                label=cfg.get("label", col),
                color=cfg.get("color"),
                linestyle=cfg.get("linestyle", "-"),
                alpha=0.6,
            )


def _plot_asset_line(ax, daily_values):
    """전체 자산 가치 변화 곡선을 강조하여 그립니다."""
    normalized = daily_values / daily_values.iloc[0]
    ax.plot(
        normalized.index,
        normalized,
        label="Total Asset (Ratio)",
        color="green",
        linewidth=2.5,
        alpha=1.0,
        zorder=10,
    )

    # 최종 자산 상태 라벨
    final_ratio = normalized.iloc[-1]
    ax.text(
        normalized.index[-1],
        final_ratio,
        f"{final_ratio:.2f} (Asset)",
        fontsize=9,
        color="green",
        fontweight="bold",
        verticalalignment="bottom",
        horizontalalignment="right",
    )
