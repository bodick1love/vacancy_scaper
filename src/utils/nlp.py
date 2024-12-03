import os

from rapidfuzz import process, fuzz


def get_most_similar_word(word, vocabulary):
    """
    Finds the most similar word from a given vocabulary based on a similarity threshold.

    This function uses the `process.extractOne` method from the `rapidfuzz` library to find the most similar
    word to the provided `word` from the `vocabulary`. The similarity is determined using the `token_sort_ratio` scorer
    from `rapidfuzz.fuzz`. If the similarity score exceeds a threshold specified by the `WORD_SIMILARITY_THRESHOLD`
    environment variable, it returns the most similar word.

    Args:
        word (str): The word to compare against the vocabulary.
        vocabulary (list of str): A list of words (vocabulary) to search for the most similar word.

    Returns:
        str: The most similar word from the vocabulary if the similarity score exceeds the threshold, otherwise None.
    """
    matched_region = process.extractOne(word, vocabulary, scorer=fuzz.token_sort_ratio)

    if matched_region and matched_region[1] > int(
        os.getenv("WORD_SIMILARITY_THRESHOLD")
    ):
        return matched_region[0]
