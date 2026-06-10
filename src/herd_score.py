def calculate_consensus(signals):

    votes = {}

    for signal in signals:

        direction = signal["direction"]

        votes[direction] = votes.get(direction, 0) + 1

    max_votes = max(votes.values())

    consensus = (max_votes / len(signals)) * 100

    return round(consensus, 2)

def calculate_weighted_consensus(signals):

    votes = {}

    for signal in signals:

        direction = signal["direction"]
        confidence = signal["confidence"]

        votes[direction] = (
            votes.get(direction, 0)
            + confidence
        )

    max_vote = max(votes.values())

    total_vote = sum(votes.values())

    score = (max_vote / total_vote) * 100

    return round(score, 2)