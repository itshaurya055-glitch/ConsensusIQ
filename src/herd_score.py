def calculate_consensus(signals):

    votes = {}

    for signal in signals:

        direction = signal["direction"]

        votes[direction] = votes.get(direction, 0) + 1

    max_votes = max(votes.values())

    consensus = (max_votes / len(signals)) * 100

    return round(consensus, 2)