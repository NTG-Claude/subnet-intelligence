def future_return_proxy(current_price: float | None, future_price: float | None) -> float | None:
    if current_price in (None, 0) or future_price is None:
        return None
    return (future_price - current_price) / current_price


def future_slippage_deterioration(current_slippage: float | None, future_slippage: float | None) -> float | None:
    if current_slippage is None or future_slippage is None:
        return None
    return future_slippage - current_slippage


def future_score_decay(current_score: float | None, future_score: float | None) -> float | None:
    if current_score is None or future_score is None:
        return None
    return future_score - current_score
