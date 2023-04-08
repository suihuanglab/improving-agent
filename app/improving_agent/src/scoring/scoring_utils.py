from typing import Union

from improving_agent.models import Result


def normalize_score(
    i_score: Union[float, int],
    min_score: Union[float, int],
    max_score: Union[float, int],
) -> float:
    return (i_score - min_score) / (max_score - min_score)


def normalize_results_scores(results: list[Result]) -> list[Result]:
    """Given a set of results, return a version normalized between
    0 and 1.
    """
    scores = [result.score for result in results]
    if not scores:
        return results
    min_score = min(scores)
    max_score = max(scores)

    if min_score == 0 and max_score == 0:
        return results

    for i, score in enumerate(scores):
        results[i].score = normalize_score(score, min_score, max_score)

    return results
