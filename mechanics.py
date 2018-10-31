"""Common module for the Sticky-Nim game
"""


# TODO test du module?


class Board:
    """The class describing a physical board. A board is a rectangle containing
    a line of slots. Each slot contains a stick at first. During a game, players
    take turns removing some of the sticks, leaving empty slots on the board
    called gaps.
    Attributes:
    - a_stick: value representing a stick on the board.
    - a_gap: value representing an empty slot on the board.
    - slots: the contents of the board. A list containing only sticks or gaps.
    TODO déplacer max_take (et play_move) vers la classe Game
    - max_take: the maximum number of sticks that a player may take on his turn.
    """
    def __init__(self, size, max_take=0, slots=None, a_gap=0, a_stick=1):
        if slots is None:
            self.slots = [a_stick] * size
        else:
            for s in slots:
                if s not in (a_gap, a_stick):
                    raise ValueError("Provided list contains unknown value ("
                        + str(s) + " instead of " + str(a_gap) + " or "
                        + str(a_stick) + ")")
            self.slots = slots
        self.a_gap = a_gap
        self.a_stick = a_stick
        self.max_take = max_take

    @classmethod
    def from_list(cls, slots, a_gap, a_stick):
        """Creates and returns a Board whose content is described by the list
        @slots. This list should contain only @a_stick and @a_gap."""
        return cls(len(slots), 0, slots, a_gap, a_stick)

    def __repr__(self):
        """Example board representation:
        <||-|||--|> (3)
        '|' are sticks, '-' are gaps, and the number on the right is max_take
        """
        board = []
        for s in self.slots:
            if s == self.a_gap:
                board.append('-')
            elif s == self.a_stick:
                board.append('|')
            else:
                board.append('?')
        return "<" + ''.join(board) + "> (" + str(self.max_take) + ")"

    def __iter__(self):
        self.iter_index = -1
        return self

    def __next__(self):
        # Iterate through the self.slots list
        self.iter_index += 1
        if self.iter_index == len(self.slots):
            raise StopIteration
        s = self.slots[self.iter_index]
        if s == self.a_gap or s == self.a_stick:
            return s
        else:
            raise ValueError("Board contains unknown value (" + str(s)
                             + " instead of " + str(self.a_gap) + " or "
                             + str(self.a_stick) + ")")

    def len(self):
        """Returns the number of sticks that this Board can contain."""
        return len(self.slots)

    def reset(self):
        """Fills this Board with sticks."""
        for i in range(len(self.slots)):
            self.slots[i] = self.a_stick

    def is_empty(self):
        """Returns True if this Board only contains gaps."""
        for slot in self.slots:
            if slot != self.a_gap:
                return False
        return True

    def play_move(self, move):
        """Plays the specified move, i.e. removes all the sticks in the slice
        [move.left:move.right] of this Board.

        If this move is not playable, may raise one of the following exceptions:
        Move.OutOfBounds, Move.TooLarge, Move.ContainsGap
        """
        if move.is_out_of_bounds_on(self):
            raise Move.OutOfBounds()
        if move.is_too_large_on(self):
            raise Move.TooLarge()
        if move.contains_gap_on(self):
            raise Move.ContainsGap()
        for i in range(move.left, move.right):
            self.slots[i] = self.a_gap


class Move:
    """Describes a move that a player might want to play.
    Attributes:
    - left
    - right
    For some Move m and some Board b, b.slots[m.left : m.right] is the slice
    where sticks are to be taken from (that is, from b[m.left] included,
    to b[m.right - 1] included).

    left should always be less than right.
    """
    def __init__(self, i1, i2):
        self.left = min(i1, i2)
        self.right = max(i1, i2)

    def size(self):
        """Returns the number of sticks that this Move would remove."""
        return self.right - self.left

    # Possible types of incorrect moves
    # (= Possible errors when trying to play a move)
    class OutOfBounds(Exception):
        pass

    class TooLarge(Exception):
        pass

    class ContainsGap(Exception):
        pass

    def is_out_of_bounds_on(self, board):
        """Returns True if this Move’s indices are out of the specified Board’s
        boundaries.
        Example:
        Board b: "<||||> (3)" (length 4, max take of 3 sticks per turn)
        Move m1: [m1.left, m1.right] = [2, 4]
        Move m2: [m2.left, m2.right] = [2, 5]
        m1 is legal on b, but m2 is out of bounds.
        """
        return self.left < 0 or self.right > board.len()

    def is_too_large_on(self, board):
        """Checks the number of sticks that this Move would remove, and returns
        True if the specified Board does not allow taking that many sticks."""
        return self.size() > board.max_take

    def contains_gap_on(self, board):
        """Returns True if the slice of the specified Board contains a gap.
        """
        return board.a_gap in board.slots[self.left:self.right]

    def is_legal_on(self, board):
        """Returns True if this Move can be played on the specified Board."""
        return not self.is_out_of_bounds_on(board)\
               and not self.is_too_large_on(board)\
               and not self.contains_gap_on(board)


class Player:
    """Attributes:
    - name: a string
    - action: a function that takes a Player and a Board, and returns the Move
      that the player wishes to play on this board.
    """
    # TODO type annotation of action_function
    def __init__(self, name, action_function):
        self.name = name
        self.action = action_function

    def ask_move(self, board):
        return self.action(self, board)


class Game:
    """Attributes:
    - players: a couple (or list of length 2) containing two Player instances.
    - board_size: the size of this game's board.
    - max_take: the maximum number of sticks a player may take on his turn.
    """
    # TODO type annotation de players : comment préciser la longueur de la liste ?
    def __init__(self, players, board_size, max_take):
        self.players = players
        self.board = Board(board_size, max_take)

    def play(self):
        """Initializes and launches a game of Sticky-Nim.
        Returns: the Player that won the game.
        """
        self.board.reset()
        current_player = 0  # alternates between 0 and 1
        while True:
            player = self.players[current_player]
            if self.board.is_empty():
                # the game ended, return the winner
                return player
            move = player.ask_move(self.board)
            self.board.play_move(move)
            # switch player for next turn
            current_player = 1 - current_player
