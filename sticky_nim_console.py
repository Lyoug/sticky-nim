"""Sticky-Nim - Console version

    This 2-player game is a variant of the game of Nim.
    Rules:
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

import random

from mechanics import Move, Settings, Player, Game
import ai

SCREEN_WIDTH = 80

# Default settings
DEFAULT_BOARD_SIZE = 20
DEFAULT_MAX_TAKE = 3

# Using a board this size and up will trigger a warning about the AI taking a
# possibly long time to load
LARGE_BOARD_WARNING = 27

# Percentage indicating how often the AI’s comments are displayed
AI_CHATTINESS = 100

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


def display_rules(settings):
    print(" Sticky-Nim ---- Rules ".center(SCREEN_WIDTH, '-'))
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
    print(f"    Starting sticks: {settings.board_size}")
    print(f"    Maximum take   : {settings.max_take} sticks per turn")
    print("-" * SCREEN_WIDTH)


def display_help():
    """Display the list of available commands."""
    print(" Sticky-Nim ---- Help ".center(SCREEN_WIDTH, '-'))
    print("""General commands:
    new       Start a new game
    settings  Change game settings (board size and max take)
    rules     Display the rules of the game
    help      Display this help
    quit      Close Sticky-Nim
In-game commands:
    xy        Take sticks from x to y
    board     Redisplay the board
    menu      Go back to the main menu""")
    # additional purposefully undocumented in-game command:
    # "cheat": shows winning moves if any
    print("-" * SCREEN_WIDTH)


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
    if 2 * len(board) + 3 > SCREEN_WIDTH:
        sep = ''
    else:
        sep = ' '
    print(sep.join(sticks).center(SCREEN_WIDTH))
    print(sep.join(letters).center(SCREEN_WIDTH))


def really_input(prompt=""):
    """Trims and returns the first user input that does not consist of only
    whitespace."""
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
    print(f"{message} ({yes}/{no}) ", end='')
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
    if len(move) > 1:
        action += _coordinates[move.right - 1]
    return action


def _cheat(game):
    # Print all winning moves if any
    # (Only works if the AI module knows about the current configuration)
    config = game.board.to_config()
    if config[0] == 1:
        if len(config) == 1:
            print("Really?")
        else:
            print("Well, it’s not like you have a choice there do you?")
        return
    if ai.loading_needed(game.settings):
        # The AI module would need additional computations to know the answer
        print(random.choice([
            "I don’t know!",
            "I’m not strong enough",
            "I would need an upgrade before I can answer",
            "This is too difficult for me"
        ]))
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
            moves.extend(game.board.list_moves(take, group, offset))
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


def errors_about_move(move, game):
    """If @move is illegal in @game, prints an error message and returns True.
    Else, returns False.
    """
    if move.is_legal_in(game):
        return False
    b = game.board
    if move.is_out_of_bounds_on(b):
        print("This move seems out of bounds")
    elif move.contains_gap_on(b):
        if b.a_stick not in b[move.left:move.right]:
            print("But… there are no sticks there")
        elif b[move.left:move.right].count(b.a_stick) <= game.settings.max_take:
            if move.strip_on(b) == move:
                print("The sticks you take need to be next to each other")
            else:
                if not move.strip_on(b).contains_gap_on(b):
                    print(f"Did you mean {to_action(move.strip_on(b))}?")
        else:
            print(random.choice([
                "Impossible move",
                "This move cannot be played",
                "Illegal move",
                "This move is illegal"
            ]))
    elif move.takes_too_many_for(game.settings.max_take):
        print(f"Please take {game.settings.max_take} sticks at most")
    return True


def human_action(player, game):
    """Returns the Move that the specified human player wishes to play in the
    specified Game.
    Allows the human to perform other commands before actually playing, like
    displaying help, rules, stopping the game, etc.
    """
    display_board(game.board)
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
            display_rules(game.settings)
        elif action == "help":
            display_help()
        elif action == "board":
            display_board(game.board)
        elif action == "cheat":
            # (This command does not show in the help)
            _cheat(game)
        elif len(action) <= 2 \
                and action[0] in _coordinates \
                and action[-1] in _coordinates:
            # convert the action into a pair of indices
            end1 = _coordinates.index(action[0])
            # using -1 allows for moves like "a" that only take one stick
            end2 = _coordinates.index(action[-1])
            # using min and max allows the user to enter coordinates from
            # right to left
            move = Move(min(end1, end2), max(end1, end2) + 1)
            if not errors_about_move(move, game):
                return move
        else:
            warn_unknown_command()


def computer_action(player, game):
    """Returns the Move that the specified AI player wishes to play in the
    specified Game.
    Displays the possible message that this player wants to say, as well as the
    move’s coordinates.
    """
    display_board(game.board)
    print(player.name + "> ", end='')
    move, message = ai.generate_move(game)
    if not move.is_legal_in(game):
        try:
            action = to_action(move)
        except IndexError:
            action = "IndexError"
        raise Exception(f"Incorrect move from the AI: "
                        f"[{move.left}, {move.right}] ({action})")
    if random.random() <= AI_CHATTINESS / 100:
        print(message, end=' ')
    print(to_action(move))
    return move


def change_settings(current_settings):
    """Makes the user input new settings for future games and returns them."""
    print("Current settings:")
    print(f"    Board size  : {current_settings.board_size}")
    print(f"    Maximum take: {current_settings.max_take} sticks per turn")
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
            print("Sorry, I’m limited to"
                  f"{len(_coordinates)} sticks on the board")
        else:
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
            break
    return Settings(board_size, max_take)


def choose_players(settings):
    """Asks the user to choose whether the players will be humans or computers.
    Returns a list of two Player objects.
    """
    players = []
    p = 0
    while p < 2:
        while True:
            print(f"Player {p + 1}: human or computer? (h/c)", end=' ')
            s = really_input().lower()
            if s in ('h', 'c'):
                break
            elif s.startswith('h'):
                s = 'h'
                print("Ah, definitely human then")
                break
            elif s.startswith('c'):
                print("Did you mean c?")
            else:
                warn_unknown_command()

        if s == 'h':
            players.append(Player(f"Player {str(p + 1)}", human_action))
        else:
            if ai.loading_needed(settings):
                if settings.board_size > LARGE_BOARD_WARNING:
                    print("Warning: the board is large, there might be a long "
                          "loading time.")
                    if not confirm("Continue?"):
                        continue   # while loop
                print("Loading…")
            ai.set_rules(settings)
            ai_names = [
                "Tin can",
                "Metal-box",
                "Recycled dishwasher",
                "Circuit board",
                "Machine",
                "Old PC",
                "Computer",
                "Robot",
                "A.I.",
                "Nim-device",
                "Omniscience",
            ]
            ai_name = f"{random.choice(ai_names)} {str(p + 1)}"
            players.append(Player(ai_name, computer_action))
        p += 1
    return players


def new_game(players, settings):
    """Lets the specified Players play a game. @players is a list of two Player.
    TODO type annotation
    Returns True if the players wish to start another game right away.
    """
    game = Game(players, settings)
    try:
        winner = game.play()
        print(f"{winner.name} won!".center(SCREEN_WIDTH))
    except PleaseRestart:
        return True
    except PleaseStop:
        return False
    else:
        return confirm("Play another game?")


def menu():
    """Main menu input loop."""
    settings = Settings(DEFAULT_BOARD_SIZE, DEFAULT_MAX_TAKE)
    while True:
        action = really_input("menu> ")
        if action in ["menu", "m"]:
            pass
        elif action == "board":
            print("Hmm, there is no ongoing game")
        elif action in ["settings", "s"]:
            settings = change_settings(settings)
        elif action in ["rules", "r"]:
            display_rules(settings)
        elif action in ["help", "h"]:
            display_help()
        elif action in ["quit", "q"]:
            raise PleaseExit()
        elif action in ["new", "n"]:
            players = choose_players(settings)
            keep_playing = True
            while keep_playing:
                print(" Sticky-Nim ---- New game ".center(SCREEN_WIDTH, '-'))
                keep_playing = new_game(players, settings)
            print("-" * SCREEN_WIDTH)
        else:
            warn_unknown_command()


# ================================ Main program ================================


if __name__ == "__main__":
    print(" Sticky-Nim ".center(SCREEN_WIDTH, '='))
    print("Type 'help' if you need some")
    try:
        menu()
    except PleaseExit:
        pass
    print(" Sticky-Nim ==== See you soon! ".center(SCREEN_WIDTH, '='))
