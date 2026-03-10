
def as_ranked(strings: list[str]) -> dict[str, int]:
    """
    Takes a list of strings, counts the occurance of duplicates, and 
    returns a dict of unique strings with their occurance counts
    """
    result = {}
    for string in strings:
        string = string.lower().strip() # sanitize for my sanity
        result[string] += 1

    return result

def accumulate_rankings(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    """
    Get your loaded or in-flight rankings and accummulate them with your
    other loaded or in-flight rankings
    """
    for string, count in left.items():
        right[string] += count

    return right