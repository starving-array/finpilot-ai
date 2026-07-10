import random

random.seed(42)

CATEGORIES = ["YES_TO_GO", "DISCIPLINED", "NON_DISCIPLINED", "NO_TO_GO"]

PROXY_WEIGHTS = {
    "repayment_history": 0.5,
    "vendor_discipline": 0.3,
    "business_continuity": 0.2,
}


def generate_label_proxies(profile: dict, traditional_data: dict) -> dict:
    vintage = profile["vintage_months"]
    bureau = traditional_data.get("bureau", {})
    gst = traditional_data.get("gst", {})
    upi = traditional_data.get("upi", {})

    proxies = {}

    if bureau:
        score = bureau.get("bureau_score", 750)
        delinquency = bureau.get("delinquency_flag", False)
        if score >= 750 and not delinquency:
            proxies["repayment_history"] = "YES_TO_GO"
        elif score >= 650:
            proxies["repayment_history"] = "DISCIPLINED"
        elif score >= 500:
            proxies["repayment_history"] = "NON_DISCIPLINED"
        else:
            proxies["repayment_history"] = "NO_TO_GO"

    if gst:
        regularity = gst.get("filing_regularity", 0.5)
        compliance = gst.get("compliance_score", 0.5)
        combined = (regularity + compliance) / 2
        if combined >= 0.8:
            proxies["vendor_discipline"] = "YES_TO_GO"
        elif combined >= 0.6:
            proxies["vendor_discipline"] = "DISCIPLINED"
        elif combined >= 0.3:
            proxies["vendor_discipline"] = "NON_DISCIPLINED"
        else:
            proxies["vendor_discipline"] = "NO_TO_GO"

    if vintage >= 12:
        if gst and gst.get("filing_regularity", 0) >= 0.7:
            proxies["business_continuity"] = "YES_TO_GO"
        elif gst:
            proxies["business_continuity"] = "DISCIPLINED"
        else:
            proxies["business_continuity"] = "NON_DISCIPLINED"
    else:
        proxies["business_continuity"] = "NO_TO_GO"

    return proxies


def compute_consensus_label(proxies: dict) -> tuple:
    if not proxies:
        return None, 0.0, {}

    category_scores = {c: 0.0 for c in CATEGORIES}
    for proxy_type, category in proxies.items():
        weight = PROXY_WEIGHTS.get(proxy_type, 0.2)
        category_scores[category] = category_scores.get(category, 0) + weight

    if not any(category_scores.values()):
        return None, 0.0, category_scores

    consensus = max(category_scores, key=category_scores.get)
    confidence = len(proxies) / 3.0  # 1 proxy = 0.33, 2 = 0.67, 3 = 1.0

    return consensus, round(confidence, 2), category_scores
