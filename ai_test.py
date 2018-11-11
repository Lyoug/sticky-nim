"""Tests for the AI module"""

import random

import ai
from mechanics import Board, Settings


def to_board(config, board_size=None, shuffle=False):
    """Returns a Board containing all the groups in @config, separated with an
    empty slot. If @board_size is specified, adds empty slots at the right end
    of the board. Raises ValueError if board_size is too small to contain the
    specified config.
    By default, @config’s group are laid on the board from largest to smallest.
    Set @shuffle to True if you want the groups to be randomly shuffled on the
    board."""
    # Necessary room: all the sticks, plus empty slots in between the groups
    min_size = sum(config) + len(config) - 1
    if board_size is None:
        board_size = min_size
    elif board_size < min_size:
        raise ValueError(f"The configuration {str(config)} does not fit on a "
                         f"board of size {board_size}")
    # no else

    conf = config[:]
    if shuffle:
        random.shuffle(conf)

    slots = []
    gap = 0
    stick = 1
    for group in conf:
        slots.extend([stick] * group + [gap])
    # remove the extra gap
    slots.pop()
    # add possible extra empty slots
    slots.extend([gap] * (board_size - len(slots)))
    return Board.from_list(slots, stick, gap)


def sizeof_configs():
    """Returns how many configurations are stored in the global _configs table
    of the ai module.
    """
    n_configs = 0
    for n in range(1, len(ai._configs)):
        for k in range(1, n + 1):
            n_configs += len(ai._configs[n][k])
    return n_configs


def composite(config1, config2):
    """Returns a new configuration made of @config1’s and @config2’s groups."""
    return sorted(config1 + config2, reverse=True)


def contains(config, sub_config):
    """Returns True if all the groups of @sub_config are found in @config."""
    for group in sub_config:
        if config.count(group) < sub_config.count(group):
            return False
    return True


def prune_losing_configs(losing_configs):
    """Returns the list of known losing configurations, barring:
    - Configs ending with a pair or several pairs of 1s
    - Configs made up of several losing sub-configs
    """
    pruned_losing_configs = []

    for c in losing_configs:
        pruned = c[:]
        # 1-group and 2-group configs are all included
        if len(pruned) <= 2:
            pruned_losing_configs.append(pruned)
            continue
        # ignore configs made of 1s only
        # pruned[0] is the largest group. If it is 1, all groups are 1s
        if pruned[0] == 1:
            continue

        # start with deleting final pairs of 1s
        n_1 = pruned.count(1)
        if n_1 > 1:
            to_remove = n_1 - n_1 % 2
            del pruned[-to_remove:]
        # then delete losing sub-configs, provided the resulting config remains
        # losing
        for lc in pruned_losing_configs[1:]:
            while contains(pruned, lc):
                # try to delete lc
                without_lc = pruned[:]
                for group in lc:
                    without_lc.remove(group)
                # if the result is still losing, confirm deletion
                if without_lc == [] or without_lc in losing_configs:
                    pruned = without_lc
                else:       # without_lc is winning
                    break   # go to the next LC
            # pruned is already empty, skip the rest of the for loop
            if not pruned:
                break
        # all losing sub-configs have been removed from pruned. If pruned is
        # still not empty, add it to the main list
        if pruned:
            pruned_losing_configs.append(pruned)
    return pruned_losing_configs


def usage():
    print("Usage :\n"
          "    python", sys.argv[0], "board_size [max_take]\n"
          "    if unspecified, max_take defaults to 3")


if __name__ == "__main__":
    import sys
    import time

    SCREEN_WIDTH = 80

    if len(sys.argv) < 2:
        usage()
        quit()
    try:
        board_size = int(sys.argv[1])
    except ValueError:
        usage()
        quit()
    try:
        max_take = int(sys.argv[2])
    except (IndexError, ValueError):
        max_take = 3

    print(" Sticky-Nim ==== AI Test ".center(SCREEN_WIDTH, '='))
    print("    Board size: ", board_size, "sticks")
    print("    Max take:   ", max_take, "sticks per turn")
    t = time.clock()
    ai.set_rules(Settings(board_size, max_take))
    t_init = round((time.clock() - t) * 1000, 1)  # milliseconds
    main_losing_configs = prune_losing_configs(ai._losing_configs)

    # print(" Configurations ".center(SCREEN_WIDTH, '-'))
    # for n in range(1, len(ai._configs)):
    #     print('-' * 10, n, "sticks", '-' * 10)
    #     for k in range(1, n + 1):
    #         lk = ai._configs[n][k]
    #         for config in lk:
    #             print(config, end=' ')
    #         print()
    # print(" Losing configurations ".center(SCREEN_WIDTH, '-'))
    # for config in ai._losing_configs:
    #     print(config)
    print(" Main losing configurations ".center(SCREEN_WIDTH, '-'))
    for config in main_losing_configs:
        print(config)

    print("-" * SCREEN_WIDTH)
    total = sizeof_configs()
    losing = len(ai._losing_configs)
    print(f"Configurations: {total}")
    print(f"Losing configurations: {losing} ({round(losing / total * 100, 2)}"
          f" %) (built in {t_init} ms)")
    print(f"Main losing configurations: {len(main_losing_configs)}")
    print("-" * SCREEN_WIDTH)

    test_configs = [
        [board_size],
        [3, 2, 1],
        [6, 5, 4, 4, 2, 1],
        [6, 5, 2, 1],
        [6, 4, 2],
        [5, 4, 1],
        [21, 1],
        [21, 5],
    ]
    test_configs.extend([[18 - n, n] for n in range(1, 10)])
    test_configs.extend([composite([n, n], [5, 1]) for n in range(1, 11)])

    for config in test_configs:
        print(config, "->", end=' ')
        if sum(config) > board_size:
            print("(unknown)")
            continue
        solutions = ai._reachable_losing_configs(config)
        if not solutions:
            print("losing")
        else:
            print(solutions)

    print("-" * SCREEN_WIDTH)
    Board.stick_char = "|"
    Board.gap_char = "-"
    test_boards = [Board.from_string(b) for b in [
        "",
        "-",
        "|",
        "-----",
        "|||||",
        "-||||",
        "||||-",
        "|-|||",
        "||-||",
        "|-|-|",
    ]]
    print("Board, Configuration, Groups")
    for board in test_boards:
        config, groups = board._process()
        print(board, config, groups, sep=', ')

    for config in test_configs:
        board = to_board(config, shuffle=True)
        config_back = board.to_config()
        if config_back != config:
            print("Incorrect conversion:")
            print("    starting config:", config)
            print("    board:", board)
            print("    resulting config:", config_back)

    print("=" * SCREEN_WIDTH)
