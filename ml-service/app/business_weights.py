from . import constants as C


def get_weights(business_type: str) -> dict[str, float]:
    return C.SIGNAL_WEIGHTS.get(business_type, C.UNIFORM_WEIGHTS)


def apply_signal_weights(signals: dict[str, float], business_type: str) -> dict[str, float]:
    weights = get_weights(business_type)
    total_weight = sum(weights.get(k, 1.0) for k in signals if signals[k] is not None)
    if total_weight == 0.0:
        weighted = {k: v for k, v in signals.items() if v is not None}
        n = len(weighted)
        return {k: v / n if n > 0 else 0.0 for k, v in weighted.items()}
    result = {}
    for k, v in signals.items():
        if v is not None:
            w = weights.get(k, 1.0)
            result[k] = (v * w) / total_weight
    return result
