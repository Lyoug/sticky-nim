"""Artificial intelligence module for the Sticky-Nim game.

    -------------------------------- Notations ---------------------------------

    A Configuration or config for short is a list of (decreasing) integers, that
    summarizes a game situation. Each integer represents a group of adjacent
    sticks.
    Example game:
    (For a more detailed commentary of this game, see the main module,
    sticky_nim_console.py)
    ===========================================
    Player  →  Board       Configuration
    ===========================================
       -    →  ||||||||||  [10]
       1    →  |||-||||||  [6, 3]
       2    →  |||-|---||  [3, 2, 1]
       1    →  --|-|---||  [2, 1, 1]
       2    →  --|-|---|-  [1, 1, 1]
       1    →  --|-|-----  [1, 1]
       2    →  ----|-----  [1]
       1    →  ----------  []  →  Player 1 lost
    ===========================================

    An n-stick k-group Configuration is a configuration made of n sticks total,
    that are divided into k groups. For instance, [6, 3] is a 9-stick 2-group
    config.

    A Losing Configuration (LC) is a configuration such that if it is my turn to
    play and I see this configuration on the board, I am bound to lose –
    provided that my opponent makes no mistake.
    Some LC examples:
    - [1]: if I see this on my turn, I can only take the last stick: I lose
      right away.
    - [1, 1, 1]: I can only take one stick, leaving my opponent with [1, 1].
      Then, they can only take one stick, leaving me with [1]. I lose.
    - [2, 2]: I have two possible moves:
      - if I take one stick (from any group of two), my opponent sees [2, 1],
        takes the group of 2, and I am left with the last stick.
      - if I take two sticks, my opponent sees [2], takes one stick from this
        last group, and leaves me with [1].
      In both cases I lose, so [2, 2] is an LC.
    It can be noted that any configuration that is not losing is a winning
    configuration.


    --------------------------------- Strategy ---------------------------------

    The idea to guarantee a win is to play a move that leaves your opponent in
    a losing configuration (LC). This AI module thus first builds the list of
    all possible LCs. Then, when asked for a move to play on a given board, it
    looks for an LC that can be reached from this board. If it finds one, it
    answers with a corresponding move. Else, it generates a random move.
"""

import random
from mechanics import Board, Move, Settings

# Interface:
# - set_rules(settings): set the board size and the maximum number of sticks
#   that can be removed on a turn. This function must be called at least once
#   before the module is able to generate moves.
# - loading_needed(settings): returns True if calling set_rules with the same
#   parameter would require additional computations.
# - generate_move(game): returns a pair containing:
#   - a Move
#   - a string about the move or the status of the game, intended as a comment
#     from the AI player about the situation, for the user interface to display.
__all__ = ["set_rules", "loading_needed", "generate_move"]

# The module parameters. To change them, call set_rules
_settings = Settings(board_size=0, max_take=0)


# ========================== Board related functions ==========================


def _process(board):
    """See _to_configs() and _to_groups().
    """
    config = []
    groups = []
    group_size = 0
    group_start = 0
    # Adding an extra slot at the end of the board avoids duplicated code after
    # the for loop below
    extended_board = Board.from_list(board._slots + [board.a_gap],
                                     board.a_stick,
                                     board.a_gap)
    for i, slot in enumerate(extended_board):
        if slot == board.a_stick:
            if group_size == 0:
                group_start = i
            group_size += 1
        else:
            if group_size > 0:   # we've reached the end of a group of sticks
                config.append(group_size)
                groups.append((group_start, group_size))
                group_size = 0
    config.sort(reverse=True)
    return config, groups


def _to_config(board):
    """Returns the configuration that describes the specified Board.
    Examples:
    Board       Configuration
    ||||||||||  [10]
    |||-||||||  [6, 3]
    |||-|---||  [3, 2, 1]
    --|-|---||  [2, 1, 1]
    """
    return _process(board)[0]


def _to_groups(board):
    """Returns a list of couples (group_start_index, group_size) that describes
    the specified Board.
    Examples:
    Board       Returned list
    ||||||||||  [(0, 10)] (a group of 10 sticks starting at index 0)
    |||-||||||  [(0, 3), (4, 6)]
    |||-|---||  [(0, 3), (4, 1), (8, 2)]
    --|-|---||  [(2, 1), (4, 1), (8, 2)]
    """
    return _process(board)[1]


def _build_move(board, take, group_size, offset=0):
    """Returns a Move that removes @take sticks in a group of @group_size
    sticks, and leaving @offset sticks at the edge of said group.
    If such a Move does not exist on the specified board, returns None.
    Example:
    With a board b represented by |||-||||||, calling _build_move(b, 3, 6, 1)
    means we want to take 3 sticks, one stick away from the edge of a 6-stick
    group.
    Returned value: Move(5, 8). Playing this move removes sticks at indices 5
    to 7 included: |||-|xxx||.
    """
    if take + offset > group_size:
        return None
    groups = _to_groups(board)
    for i_start, size in groups:
        if size == group_size:
            left = i_start + offset
            right = left + take
            return Move(left, right)
    else:  # No group was found with the right size
        return None


# ====================== Configuration related functions ======================

# Table of all possible configurations (up to some maximum number of sticks)
# _configs[n] is the table of n-stick configs
# _configs[n][k] is the list of n-stick k-group configs
_configs = []
_configs.append([])   # adding the (empty) list of 0-stick configs

# List of known losing configurations
_losing_configs = []

# A dictionary to backup the LC-lists that were built with different values of
# max_take, so that they need not be recomputed when changing settings.
# keys: max_take
# values: (board_size, _losing_configs)
_losing_backup = {}


def _move_exists(config_from, config_to, max_take):
    """Returns True if when in the situation @config_from, you can play a move
    that removes at most @max_take sticks and gets you to the situation
    @config_to.
    """
    # After a move, the number of groups can either:
    # - remain the same
    # - decrease by one (if you take a group’s last sticks)
    # - increase by one (if you split a group by taking sticks in its middle)
    if abs(len(config_from) - len(config_to)) > 1:
        return False

    # You have to take between 1 and max_take sticks per turn
    take = sum(config_from) - sum(config_to)
    if take < 1 or take > max_take:
        return False

    # Since playing a move can only modify one group of the starting config,
    # every group of config_from must be found again in config_to, except for
    # one (the group you take sticks from).
    c_from = config_from[:]
    for group in config_to:
        if group in c_from:
            c_from.remove(group)
    return len(c_from) == 1


def _describe_move_between(config_from, config_to):
    """Returns a triplet of integers describing what move you need to make to
    get from @config_from to @config_to:
    - the number of sticks to take
    - the size of the group to take sticks from
    - the number of sticks to leave on the edge of such a group
    If no move exists between the two specified configs, returns None.
    """
    take = sum(config_from) - sum(config_to)
    if not _move_exists(config_from, config_to, take):
        return None
    # deleting common groups
    c_from = config_from[:]
    c_to = config_to[:]
    for group in config_to:
        if group in c_from:
            c_from.remove(group)
            c_to.remove(group)
    # there can be only one group left in c_from (see _move_exists)
    size_of_group_to_take_from = c_from[0]
    # in c_to, there can be:
    # - 0 group left: taking all the sticks in c_from’s group
    # - 1 group left: taking the sticks on the edge of c_from’s group
    # - 2 groups left: taking the sticks in the middle of c_from’s group
    if len(c_to) <= 1:
        offset = 0
    else:  # len(c_to) == 2
        # randomly choosing between c_to[0] and c_to[1] (symmetrical offsets)
        # for more variety in the AI’s moves.
        offset = c_to[random.choice([0, 1])]
    return take, size_of_group_to_take_from, offset


def _build_configs(up_to, start_from=1):
    """Fills the table of all configurations made up of @up_to sticks and fewer.
    If you know the table has already been computed up to some value N, you can
    set @start_from to N + 1 to avoid recomputing.
    """
    global _configs
    for n in range(start_from, up_to + 1):
        # n-stick config list initialisation
        _configs.append([])
        # no 0-group configs
        _configs[n].append([])
        # the only 1-group config: one group of n sticks
        _configs[n].append([[n]])
        for k in range(2, n + 1):
            # Creating the list of n-stick k-group configs
            # Such a config can either be:
            # A. an (n-1)-stick (k-1)-group config to which you add a 1-stick
            #    group
            # B. an (n-k)-stick k-group config in which you add one stick to
            #    every group
            # More info: https://en.wikipedia.org/wiki/Partition_(number_theory)
            _configs[n].append([])
            # Set A
            new_configs = []
            for c in _configs[n - 1][k - 1]:
                new_c = c[:]
                new_c.append(1)    # adding the 1-stick group
                new_configs.append(new_c)
            _configs[n][k].extend(new_configs)
            # Set B
            if k > n - k:
                continue
            new_configs = []
            for c in _configs[n - k][k]:
                # adding a stick to every group
                new_configs.append([x + 1 for x in c])
            _configs[n][k].extend(new_configs)


# Slowest function. On my computer (core i5 from 2018):
# @up_to   Time
# 20       ~100 ms
# 30       ~10 s
# 40       ~10 min
def _build_losing_configs(up_to, max_take, start_from=1):
    """Builds the list of all losing configurations made of @up_to sticks or
    fewer.
    Requires that the _configs table has been computed (with _build_configs)
    at least up to @up_to.
    """
    # For all configs, scan the list of known LCs, looking for an LC that can
    # be reached from the current config. If none is found, it means this
    # current config is losing: add it to the list.
    global _losing_configs
    for n in range(start_from, up_to + 1):
        # shortcut: when n is odd, no n-stick config is losing except for
        # [1, 1, ..., 1] (I don't have proof for this).
        if n % 2 == 1:
            _losing_configs.append([1] * n)
            continue
        for k in range(1, n + 1):
            for config in _configs[n][k]:
                for lc in _losing_configs:
                    if _move_exists(config, lc, max_take):
                        break
                else:  # no break
                    _losing_configs.append(config)


def _reachable_losing_configs(config_from):
    """Returns the list of all configs in @losing_configs that can be reached in
    one move from @config_from.
    Note: if the result is not empty, it means @config_from is a winning config.
    """
    return [c for c in _losing_configs
            if _move_exists(config_from, c, _settings.max_take)]


def _losing_message_about(losing_config):
    """Returns a string about a losing config, intended as a comment from the
    AI player about the situation, for the user interface to display.
    """
    # the game is ending right away
    if losing_config == [1]:
        messages = [
            "I yield!",
            "I admit defeat.",
            "Well played.",
            "Bravo!",
            "A worthy opponent indeed.",
        ]
        # if the game was winnable in one move
        if _settings.max_take >= _settings.board_size - 1:
            additional_comments = [
                "(Already?)",
                "(Wasn’t that a little short?)",
                "(Or was it just that easy?)",
                "(But I wonder if you really deserve that?)",
                "(Or are you?)"
            ]
            return random.choice([' '.join([message, comment]) \
                for message, comment in zip(messages, additional_comments)])
        else:
            return random.choice(messages)
    # only an odd number of groups of 1 (= rather obvious incoming defeat)
    elif losing_config[0] == 1 and sum(losing_config) % 2 == 1:
        return random.choice([
            "Oh no–",
            "I’m in trouble…",
            "The end is near…",
            "Ouch.",
            "I know where this is going. I don’t like it.",
            "I have a bad feeling about this."
        ])
    # nearing the end of the game
    elif sum(losing_config) <= _settings.board_size / 3:
        return random.choice([
            "Looks like you’re quite strong.",
            "Oh man!",
            "Really?",
            "Unbelievable.",
            "You had me from the beginning didn’t you.",
            "You’ve been practising, it seems."
        ])
    # general case: defeat unless our opponent makes a mistake
    else:
        return random.choice([
            "Hmm…",
            "Can’t decide…",
            "Making my mind up…",
            "Just a second…",
            "It’s not that easy…",
            "Not bad.",
            "Oh, that’s good."
        ])


def _winning_message_about(config, target):
    """Returns a string about a winning config, intended as a comment from the
    AI player about the situation, for the user interface to display.
    @target is the config of the board after the move that the AI is about to
    play.
    """
    # the game will end after the opponent’s next move
    if target == [1]:
        messages = [
            "Well played.",
            "You fought well.",
            "The final blow.",
            "This is it.",
            "There we go,",
            "You’ll do better next time :)",
            "Up for revenge?",
            "Let’s go for another one!",
            "Sorry!",
            "I love this game."
        ]
    # only groups of 1 are left (= rather obvious incoming victory)
    elif config[0] == 1:
        messages = [
            "I’m feeling good.",
            "Seems easy enough.",
            "Very good.",
            "Only one way now, right?",
            "I don’t have a choice, but I don’t mind."
        ]
    # general case: victory (unless we make a mistake…)
    else:
        messages = [
            "All right,",
            "I’m playing",
            "Let’s try",
            "Let’s say,",
            "Okay,",
            "Why not",
            "Tell me what you think of",
            "I feel like playing",
            "I’m going for",
            "Try and counter this:",
            "I came up with"
        ]
    return random.choice(messages)


# =============================== Main functions ===============================


def set_rules(settings):
    """Defines the settings that the module is going to use when asked to play
    moves. Needs to be called at least once before generate_moves can be called.
    """
    global _configs
    global _losing_configs
    size = settings.board_size
    max_take = settings.max_take
    # fetch backed up data if any
    known_size, _losing_configs = \
        _losing_backup[max_take] if max_take in _losing_backup else (0, [])

    _settings.board_size = size
    _settings.max_take = max_take
    _build_configs(up_to=size, start_from=len(_configs))
    _build_losing_configs(size, max_take, start_from=known_size + 1)
    # if we've built new things, back them up
    if loading_needed(settings):
        _losing_backup[max_take] = (size, _losing_configs)


def loading_needed(settings):
    """Returns True if calling set_rules with the same parameters would require
    additional computations.
    """
    return settings.max_take not in _losing_backup \
        or settings.board_size > _losing_backup[settings.max_take][0]


def generate_move(game):
    """Returns a pair containing:
    - a Move
    - a string about the move or the status of the game, intended as a comment
      from the AI player about the situation, for the user interface to display.
    Requires that set_rules has been called before.
    """
    if game.settings.board_size != _settings.board_size \
            or game.settings.max_take != _settings.max_take:
        raise ValueError("Inconsistent settings between the AI and the game")
    config = _to_config(game.board)
    targets = _reachable_losing_configs(config)
    if targets is None:
        raise Exception("This board was not studied. There was probably an "
                        "error while initializing the " + __name__ + "module.")
    elif targets:
        # The AI can win
        target = random.choice(targets)
        take, group, offset = _describe_move_between(config, target)
        message = _winning_message_about(config, target)
    else:
        # The AI is in a losing situation
        # Let’s generate a random move. We need:
        # - a group to touch
        # - a number of sticks to take from this group
        # - a number of sticks to leave on the edge of the group
        group = random.choice(config)
        take = random.randint(1, min(game.settings.max_take, group))
        offset = random.randint(0, group - take)
        message = _losing_message_about(config)
    # TODO add CHATTINESS setting?
    if random.random() > 1:
        message = ""
    return _build_move(game.board, take, group, offset), message


# =============================== Module testing ===============================


def _to_board(config, board_size=None, shuffle=False):
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


def _sizeof_configs():
    """Returns how many configurations are stored in the global _configs table.
    """
    n_configs = 0
    for n in range(1, len(_configs)):
        for k in range(1, n + 1):
            n_configs += len(_configs[n][k])
    return n_configs


def _composite(config1, config2):
    """Returns a new configuration made of @config1’s and @config2’s groups.
    """
    return sorted(config1 + config2, reverse=True)


def _contains(config, sub_config):
    """Returns True if all the groups of @sub_config are found in @config.
    """
    for group in sub_config:
        if config.count(group) < sub_config.count(group):
            return False
    return True


def _prune_losing_configs(losing_configs):
    """Returns the list of known losing configurations, barring:
    - Configs ending with a pair or pairs of 1
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
            while _contains(pruned, lc):
                # try to delete lc
                without_lc = pruned[:]
                for group in lc:
                    without_lc.remove(group)
                # if the result is still losing, confirm deletion
                if without_lc == [] or without_lc in losing_configs:
                    pruned = without_lc
                else:       # without_lc is winning
                    break   # go to the next LC
            # the config was only made of losing sub-configs
            if pruned == []:
                break
        # all losing sub-configs have been removed from pruned. If pruned is
        # still not empty, add it to the main list
        if pruned != []:
            pruned_losing_configs.append(pruned)
    return pruned_losing_configs


def _usage():
    print("Usage :\n"
          "    python", sys.argv[0], "board_size [max_take]\n"
          "    if unspecified, max_take defaults to 3")


if __name__ == "__main__":
    import sys
    import time

    SCREEN_WIDTH = 80

    if len(sys.argv) < 2:
        _usage()
        quit()
    try:
        _settings.board_size = int(sys.argv[1])
    except ValueError:
        _usage()
        quit()
    try:
        _settings.max_take = int(sys.argv[2])
    # TODO handle ValueError and IndexError
    except:
        _settings.max_take = 3

    print(" Sticky-Nim ==== AI Test ".center(SCREEN_WIDTH, '='))
    print("    Board size: ", _settings.board_size, "sticks")
    print("    Max take:   ", _settings.max_take, "sticks per turn")
    t = time.clock()
    set_rules(_settings)
    t_init = round((time.clock() - t) * 1000, 1)  # milliseconds
    main_losing_configs = _prune_losing_configs(_losing_configs)

    print(" Configurations ".center(SCREEN_WIDTH, '-'))
    for n in range(1, len(_configs)):
        print('-' * 10, n, "sticks", '-' * 10)
        for k in range(1, n + 1):
            lk = _configs[n][k]
            for config in lk:
                print(config, end = ' ')
            print()
    print(" Losing configurations ".center(SCREEN_WIDTH, '-'))
    for config in _losing_configs:
       print(config)
    print(" Main losing configurations ".center(SCREEN_WIDTH, '-'))
    for config in main_losing_configs:
        print(config)

    print("-" * SCREEN_WIDTH)
    total = _sizeof_configs()
    losing = len(_losing_configs)
    print(f"Configurations: {total}")
    print(f"Losing configurations: {losing} ({round(losing / total * 100, 2)}"
          f" %) (built in {t_init} ms)")
    print(f"Main losing configurations: {len(main_losing_configs)}")
    print("-" * SCREEN_WIDTH)

    test_configs = [
        [_settings.board_size],
        [3, 2, 1],
        [6, 5, 4, 4, 2, 1],
        [6, 5, 2, 1],
        [6, 4, 2],
        [5, 4, 1],
        [21, 1],
        [21, 5],
    ]
    test_configs.extend([[18 - n, n] for n in range(1, 10)])
    test_configs.extend([_composite([n, n], [5, 1]) for n in range(1, 11)])

    for config in test_configs:
        print(config, "->", end=' ')
        if sum(config) > _settings.board_size:
            print("(unknown)")
            continue
        solutions = _reachable_losing_configs(config)
        if solutions == []:
            print("losing")
        else:
            print(solutions)

    print("-" * SCREEN_WIDTH)
    test_boards = [Board.from_list(list(b), "l", "-") for b in [
        "",
        "-",
        "l",
        "-----",
        "lllll",
        "-llll",
        "llll-",
        "l-lll",
        "ll-ll",
        "l-l-l",
    ]]
    print("Board, Configuration, Groups")
    for board in test_boards:
        config, groups = _process(board)
        print(board, config, groups, sep=', ')

    for config in test_configs:
        board = _to_board(config, shuffle=True)
        config_back = _to_config(board)
        if config_back != config:
            print("Incorrect conversion:")
            print("    starting config:", config)
            print("    board:", board)
            print("    resulting config:", config_back)

    print("=" * SCREEN_WIDTH)
