from typing import Union

from improving_agent.models import Result


def normalize_round_score(i_score: float, m: float, b: float) -> float:
    return round(m * i_score + b, 3)


def normalize_results_scores(results: list[Result]) -> list[Result]:
    """Given a set of results, return a version normalized between
    0.01 and 1.
    """

    scores = [result.analyses[0].score for result in results]
    if not scores:
        return results
    min_score = min(scores)
    max_score = max(scores)

    if min_score == 0 and max_score == 0:
        return results

    if len(scores) == 1:
        results[0].analyses[0].score = 1
        return results

    desired_max = 1
    desired_min = 0.01
    m = (desired_max - desired_min) / (max_score - min_score)
    b = desired_min - m * min_score
    for i, score in enumerate(scores):
        results[i].analyses[0].score = normalize_round_score(score, m, b)

    return results
