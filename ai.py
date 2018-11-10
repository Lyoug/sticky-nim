"""Artificial intelligence module for the Sticky-Nim game.

    Some more definitions about Configurations:

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
from mechanics import Settings

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
            # must be the same size as messages
            additional_comments = [
                "(Already?)",
                "(Wasn’t that a little short?)",
                "(Or was it just that easy?)",
                "(But I wonder if you really deserve that?)",
                "(Or are you?)"
            ]
            return random.choice([' '.join([message, comment])
                                  for message, comment
                                  in zip(messages, additional_comments)])
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
    config = game.board.to_config()
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
    move = random.choice(game.board.list_moves(take, group, offset))
    return move, message
