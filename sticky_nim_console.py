"""Sticky-Nim - Console version

    This game is a variant of the game of Nim.
    Rules:
    - 2 players
    - Start with a line of sticks: ||||||||||
    - On their turn, a player may take up to 3 sticks from the line. These
      sticks can be anywhere, but they need to be next to each other.
    - Whoever takes the last stick loses.

    The starting quantity of sticks and the number of sticks you are allowed
    to take every turn can be customized.

    Example game:
    ========================================================================
    Player  Action                           →  Board
    ========================================================================
            (Start)                          →  ||||||||||
       1    Takes one stick                  →  |||-||||||
       2    Takes three sticks               →  |||-|---||
       1    Takes two sticks                 →  --|-|---||
       2    Takes one stick                  →  --|-|---|-
       1    Cannot take more than one stick  →  --|-|-----
       2    Doesn't have a choice either     →  ----|-----
       1    Has to take the last one         →  ----------  →  Player 1 lost
    ========================================================================

    Example of an illegal move:
    Say the board looks like this |||-|-||||. You cannot take these two marked
    sticks |||-x-x||| because they are not next to each other.
"""

import sys
import random

from mechanics import Move, Player, Game
import ai

DEFAULT_BOARD_SIZE = 20
DEFAULT_MAX_TAKE = 3
# Using a board this size and up will trigger a warning about the AI taking a
# possibly long time to load
LARGE_BOARD_WARNING = 27

_settings = {
    'board_size': -1,
    'max_take': -1,
    'screen_width': 80  # TODO paramétrable par l'utilisateur ? auto-ajustable ?
}

# The board typically contains about 20 sticks. This interface is limited to
# 62 sticks, labeled a-z, then A-Z, then 0-9 (26 + 26 + 10 = 62).
# This is more than enough since the game does not get much more interesting
# when the board gets really big.
_coordinates = [chr(i) for i in range(ord('a'), ord('z') + 1)] \
    + [chr(i) for i in range(ord('A'), ord('Z') + 1)] \
    + [chr(i) for i in range(ord('0'), ord('9') + 1)]


class PleaseRestart(Exception):
    """Raised during a game when a player wants to restart said game."""
    pass


class PleaseStop(Exception):
    """Raised during a game when a player wants to stop and go back to the main
    menu."""
    pass


class PleaseExit(Exception):
    """Raised when a player wants to exit the program."""
    pass


def display_rules():
    print(" Sticky-Nim ---- Rules ".center(_settings['screen_width'], '-'))
    print("""This 2-player game is a variant of the game of Nim.
- Start with a line of sticks: ||||||||||
- On your turn, you may take up to 3 sticks from the line, anywhere you want,
  but they need to be next to each other.
- Whoever takes the last stick loses.

Example game:
========================================================================
Player  Action                           →  Board
========================================================================
        (Start)                          →  ||||||||||
   1    Takes one stick                  →  |||-||||||
   2    Takes three sticks               →  |||-|---||
   1    Takes two sticks                 →  --|-|---||
   2    Takes one stick                  →  --|-|---|-
   1    Cannot take more than one stick  →  --|-|-----
   2    Doesn't have a choice either     →  ----|-----
   1    Has to take the last one         →  ----------  →  Player 1 lost
========================================================================

The starting quantity of sticks and the maximum number of sticks you are
allowed to take every turn can be customized. Current settings:""")
    print("    Starting sticks:", _settings['board_size'])
    print("    Maximum take   :", _settings['max_take'], "sticks per turn")
    print("-" * _settings['screen_width'])


def display_help():
    """Display the list of available commands.
    """
    print(" Sticky-Nim ---- Help ".center(_settings['screen_width'], '-'))
    print("General commands:")
    print("    new       Start a new game")
    print("    settings  Change game settings (board size and max take)")
    print("    rules     Display the rules of the game")
    print("    help      Display this help")
    print("    quit      Close Sticky-Nim")
    print("In-game commands:")
    print("    xy        Take sticks from x to y")
    print("    board     Redisplay the board")
    print("    menu      Go back to the main menu")
    # additional purposefully undocumented in-game command:
    # "cheat": shows winning moves if any
    print("-" * _settings['screen_width'])


def display_board(board):
    """Displays the game board as shown:

    < | | - | | | | - - | | | | | | | - - - | >
      a b   d e f g     j k l m n o p       t

    The '|' are the remaining sticks, the '-' are the empty slots.
    If the board is too large to fit on screen, the space in between every slot
    is not printed.
    """
    sticks = ['<']
    letters = [' ']
    for i, slot in enumerate(board):
        if slot == board.a_stick:
            sticks.append('|')
            letters.append(_coordinates[i])
        else:
            sticks.append('-')
            letters.append(' ')
    sticks.append('>')
    letters.append(' ')
    if 2 * board.len() + 3 > _settings['screen_width']:
        sep = ''
    else:
        sep = ' '
    print(sep.join(sticks).center(_settings['screen_width']))
    print(sep.join(letters).center(_settings['screen_width']))


def really_input(prompt=""):
    """Trims and returns the first user input that does not consist of only
    whitespace.
    """
    while True:
        s = input(prompt).strip()
        if s != "":
            return s


def confirm(message, yes="y", no="n"):
    """Displays @message, then asks for user input. If it reads @yes, returns
    True; if it reads @no, returns False (case insensitive). If it reads
    something else, returns False but displays a warning message first.
    Typical use:
    if confirm("Continue?"):
        # Code if the user typed "y"
    else:
        # Code if the user typed something else
    """
    print(message + " (" + yes + "/" + no + ") ", end='')
    choice = really_input().lower()
    if choice == yes:
        return True
    else:
        if choice != no:
            print("I’ll take this as a no :)")
        return False


def to_action(move):
    """Returns the string that a human would have to type if they wanted to play
    the specified move.
    """
    action = _coordinates[move.left]
    if move.size() > 1:
        action += _coordinates[move.right - 1]
    return action


def _cheat(board):
    # Print all winning moves if any
    # (Only works if the AI module knows about the current configuration)
    config = ai._to_config(board)
    if config[0] == 1:
        if len(config) == 1:
            print("Really?")
        else:
            print("Well, it’s not like you have a choice there do you?")
        return
    if ai.loading_needed(_settings['board_size'], _settings['max_take']):
        # The AI module would need additional computations to know the answer
        print("I don’t know!")
        return
    solutions = ai._reachable_losing_configs(config)
    if not solutions:
        print(random.choice([
            "Just do whatever",
            "Looks all the same to me",
            "It won’t change anything",
            "It’s all said and done anyway",
            "I’m not going to be able to help you there",
            "Forget it, your opponent is too strong",
            "I don’t see any good move",
            "I’m afraid there’s not much you can do"
        ]))
    else:
        moves = []
        for target in solutions:
            take, group, offset = ai._describe_move_between(config, target)
            moves.append(ai._build_move(board, take, group, offset))
        print(', '.join(sorted([to_action(m) for m in moves])))


def warn_unknown_command():
    """Print a message to warn the user that the command he typed is invalid.
    """
    print(random.choice([
        "I did not get that",
        "Sorry?",
        "I do not know this command",
        "Unknown command",
        "Invalid command",
        "Unrecognized input"
    ]))


def human_action(player, board):
    """Returns the Move that the specified human player wishes to play on the
    specified Board.
    Allows the human to perform other commands before actually playing, like
    displaying help, rules, stopping the game, etc.
    """
    display_board(board)
    while True:
        action = really_input(player.name + "> ")
        if action == "menu":
            if confirm("Stop this game?"):
                raise PleaseStop()
        elif action == "new":
            if confirm("Restart this game?"):
                raise PleaseRestart()
        elif action == "quit":
            if confirm("Quit Sticky-Nim?"):
                raise PleaseExit()
        elif action == "settings":
            print("Please go back to the main menu first")
        elif action == "rules":
            display_rules()
        elif action == "help":
            display_help()
        elif action == "board":
            display_board(board)
        elif action == "cheat":
            # (This command does not show in the help)
            _cheat(board)
        elif len(action) <= 2 \
                and action[0] in _coordinates \
                and action[-1] in _coordinates:
            # convert the action into a pair of indices
            end1 = _coordinates.index(action[0])
            # using -1 to allow moves like "a" that only take one stick
            end2 = _coordinates.index(action[-1])
            # using min and max allows the user to enter coordinates from
            # right to left
            move = Move(min(end1, end2), max(end1, end2) + 1)
            if move.is_out_of_bounds_on(board):
                print("This move seems out of bounds")
            elif move.contains_gap_on(board):
                # TODO more detailed error message if size is legal and there
                # are sticks on both sides
                print("Impossible move")
            elif move.is_too_large_on(board):
                print("Take", board.max_take, "sticks at most!")
            else:
                return move
        else:
            warn_unknown_command()


def computer_action(player, board):
    """Returns the Move that the specified AI player wishes to play on the
    specified board.
    Displays the possible message that this player wants to say, as well as the
    move’s coordinates.
    """
    display_board(board)
    print(player.name + "> ", end='')
    move, message = ai.generate_move(board)
    if not move.is_legal_on(board):
        raise Exception("Incorrect move from the AI: " + str(move))
    if message != "":
        print(message, end=' ')
    print(to_action(move))
    return move


def change_settings():
    """Makes the user input new settings for future games.
    """
    print("Current settings:")
    print("    Starting sticks:", _settings['board_size'])
    print("    Maximum take   :", _settings['max_take'], "sticks per turn")
    while True:
        print("New board size?", end=' ')
        try:
            board_size = int(really_input())
        except ValueError:
            warn_unknown_command()
            continue
        if board_size <= 0:
            print("This might be a little too small")
        elif board_size > len(_coordinates):
            print("Sorry, I’m limited to",
                  len(_coordinates), "sticks on the board")
        else:
            _settings["board_size"] = board_size
            break
    while True:
        print("Maximum take per turn?", end=' ')
        try:
            max_take = int(really_input())
        except ValueError:
            warn_unknown_command()
            continue
        if max_take <= 0:
            print("Hmm, negative sticks… Too complicated for me")
        else:
            _settings['max_take'] = max_take
            break


def choose_players():
    """Asks the user to choose whether the players will be humans or computers.
    Returns a list of two Player objects.
    """
    players = []
    p = 0
    while p < 2:
        print(f"Player {p + 1}: human or computer? (h/c)", end=' ')
        s = really_input().lower()
        if s == 'c':
            if ai.loading_needed(_settings['board_size'],
                                 _settings['max_take']):
                if _settings['board_size'] > LARGE_BOARD_WARNING:
                    print("Warning: the board is large, there might be a long "
                          "loading time.")
                    if not confirm("Continue?"):
                        continue
                print("Loading…")
            ai.set_rules(_settings['board_size'], _settings['max_take'])
            ai_names = [
                "Computer",
                "Robot",
                "Machine",
                "A.I.",
                "Metal-box",
                "Circuit board",
                "Old PC",
                "Nim-device",
            ]
            ai_name = " ".join([random.choice(ai_names), str(p + 1)])
            players.append(Player(ai_name, computer_action))
        else:
            # TODO use startswith
            if s != 'h':
                print("Ah, definitely human then")
            players.append(Player("Player " + str(p + 1), human_action))
        p += 1
    return players


def new_game(players):
    """Lets the specified Players play a game. @players is a list of two Player.
    TODO type annotation
    Returns True if the players wish to start another game right away.
    """
    game = Game(players, _settings['board_size'], _settings['max_take'])
    try:
        winner = game.play()
        print(' '.join([winner.name, "won!"])
              .center(_settings['screen_width']))
    except PleaseRestart:
        return True
    except PleaseStop:
        return False
    else:
        return confirm("Play another game?")


def menu(width):
    """Main menu input loop."""
    while True:
        action = really_input("menu> ")
        if action in ["menu", "m"]:
            pass
        elif action == "board":
            print("Hmm, there is no ongoing game")
        elif action in ["settings", "s"]:
            change_settings()
        elif action in ["rules", "r"]:
            display_rules()
        elif action in ["help", "h"]:
            display_help()
        elif action in ["quit", "q"]:
            raise PleaseExit()
        elif action in ["new", "n"]:
            players = choose_players()
            keep_playing = True
            while keep_playing:
                print(" Sticky-Nim ---- New game ".center(width, '-'))
                keep_playing = new_game(players)
            print("-" * width)
        else:
            warn_unknown_command()


def parse_command_line():
    """Reads command line arguments if any, and fills the _settings global
    dictionary accordingly. Giving no argument results in the default
    settings being used. Giving incorrect arguments result in the program
    exiting.
    """
    # TODO finer exception handling: ValueError, IndexError
    try:
        size = int(sys.argv[1])
    except:
        size = DEFAULT_BOARD_SIZE
    if size <= 0:
        print("The board size must be positive")
        quit()
    if size > len(_coordinates):
        print("Sorry, this interface is limited to",
              len(_coordinates), "sticks")
        quit()
    _settings['board_size'] = size

    try:
        max_take = int(sys.argv[2])
    except:
        max_take = DEFAULT_MAX_TAKE
    if max_take <= 0:
        print("The maximum take must be positive")
        quit()
    _settings['max_take'] = max_take


# ================================ Main program ================================


if __name__ == "__main__":
    parse_command_line()
    print(" Sticky-Nim ".center(_settings['screen_width'], '='))
    print("Type 'help' if you need some")
    try:
        menu(_settings['screen_width'])
    except PleaseExit:
        pass
    print(" Sticky-Nim ==== See you soon! ".center(
        _settings['screen_width'], '='))
