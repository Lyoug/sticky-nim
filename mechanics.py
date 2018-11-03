"""Common module for the Sticky-Nim game
    Describes the Board, Move, Player, Settings and Game classes.
"""

# TODO test du module?

from collections import Sequence


class Board(Sequence):
    """The class describing a physical board. A board is a rectangle containing
    a line of slots. Each slot contains a stick at first. During a game, players
    take turns removing some of the sticks, leaving empty slots on the board
    called gaps.
    Attributes:
    - a_stick: value representing a stick on the board.
    - a_gap: value representing an empty slot on the board.
    - slots: the contents of the board. A list containing only sticks or gaps
      (i.e. instances of a_stick or a_gap).
    """
    def __init__(self, size, slots=None, a_stick=1, a_gap=0):
        if slots is None:
            self._slots = [a_stick] * size
        else:
            for s in slots:
                if s not in (a_stick, a_gap):
                    raise ValueError("Provided list contains unknown value ("
                                     f"{str(s)} instead of {str(a_gap)} "
                                     f"or {str(a_stick)})")
            self._slots = slots
        self.a_stick = a_stick
        self.a_gap = a_gap
        super().__init__()

    @classmethod
    def from_list(cls, slots, a_stick, a_gap):
        """Creates and returns a Board whose content is described by the list
        @slots. This list should contain only @a_stick and @a_gap."""
        return cls(len(slots), slots, a_stick, a_gap)

    def __eq__(self, other):
        """Returns True if the specified Boards are the same length and contain
        sticks and gaps at the same spots."""
        return str(self) == str(other)

    def __repr__(self):
        return f"{self._slots} (sticks: {self.a_stick}, gaps: {self.a_gap})"

    def __str__(self):
        """Example board representation:
        ||-|||--|
        '|' are sticks, '-' are gaps.
        """
        board = []
        for s in self._slots:
            if s == self.a_stick:
                board.append('|')
            elif s == self.a_gap:
                board.append('-')
            else:
                raise ValueError("Board contains unknown value "
                                 f"{str(s)} instead of {str(self.a_stick)} "
                                 f"or {str(self.a_gap)}")
        return ''.join(board)

    def __iter__(self):
        self.iter_index = -1
        return self

    def __next__(self):
        # Iterate through the self._slots list
        self.iter_index += 1
        if self.iter_index == len(self._slots):
            raise StopIteration
        s = self._slots[self.iter_index]
        if s == self.a_gap or s == self.a_stick:
            return s
        else:
            raise ValueError(f"Board contains unknown value ({str(s)} instead "
                             f"of {str(self.a_stick)} or {str(self.a_gap)})")

    def __getitem__(self, item):
        """If @item is an integer, returns the content of this Board at the
        corresponding index. If @item is a slice or a Move, returns the
        corresponding sub-Board.
        """
        if isinstance(item, Move):
            return __class__.from_list(self._slots[item.left:item.right],
                                       self.a_stick,
                                       self.a_gap)
        if isinstance(item, slice):
            return __class__.from_list(self._slots[item],
                                       self.a_stick,
                                       self.a_gap)
        else:
            return self._slots[item]

    def __len__(self):
        """Returns the number of sticks that this Board can contain.
        """
        return len(self._slots)

    def reset(self):
        """Fills this Board with sticks.
        """
        for i in range(len(self._slots)):
            self._slots[i] = self.a_stick

    def is_empty(self):
        """Returns True if this Board only contains gaps.
        """
        return not self.a_stick in self._slots

    def play_move(self, move):
        """Plays the specified move, i.e. removes all the sticks in the slice
        [move.left:move.right] of this Board.
        Returns True if the slice contained only sticks (i.e. the move is
        probably legal), False if there was any gap in the slice.
        """
        move_contained_gap = False
        for i in range(move.left, move.right):
            if self._slots[i] == self.a_gap:
                move_contained_gap = True
            self._slots[i] = self.a_gap
        return not move_contained_gap


class Move:
    """Describes a move that a player might want to play, as a pair of indices.
    Attributes:
    - left
    - right
    For some Move m and some Board b, b[m.left:m.right] is the slice of b where
    sticks are to be taken from (that is, from b[m.left] included, to
    b[m.right - 1] included).

    left should always be less than right. Using negative indices may result in
    undefined behavior.
    """
    def __init__(self, index_1, index_2):
        self.left = min(index_1, index_2)
        self.right = max(index_1, index_2)

    def __repr__(self):
        return f"[{self.left}:{self.right}]"

    def __len__(self):
        """Returns the number of sticks that this Move would remove on an
        (infinitely long) board filled with sticks.
        """
        return self.right - self.left

    def __eq__(self, other):
        if self is None:
            return other is None
        else:
            return other is not None \
                and self.left == other.left and self.right == other.right

    def is_out_of_bounds_on(self, board):
        """Returns True if this Move’s indices are out of the specified Board’s
        boundaries.
        Example:
        Board b: "<||||>" (length 4)
        Move m1: [m1.left, m1.right] = [2, 4]
        Move m2: [m2.left, m2.right] = [2, 5]
        m1 is legal on b, but m2 is out of bounds.
        """
        return self.left < 0 or self.right > len(board)

    def contains_gap_on(self, board):
        """Returns True if the slice of the specified Board contains a gap.
        """
        return board.a_gap in board[self.left:self.right]

    def takes_too_many_for(self, max_take):
        """Returns True if the number of sticks that this Move would remove is
        above @max_take.
        """
        return len(self) > max_take

    def is_legal_in(self, game):
        """Returns True if this Move can be played in the specified Game."""
        return not self.is_out_of_bounds_on(game.board) \
            and not self.contains_gap_on(game.board) \
            and not self.takes_too_many_for(game.settings.max_take)

    def strip_on(self, board):
        """Returns a new Move that is stripped of any gaps that the specified
        Board may contain at the edges of this Move. If this Move contains only
        gaps, returns None.
        Example on a board b that looks like "|-|-||--|":
        # m is about this slice of b:
        # |-|-||--|
        #  xxxxxxx
        m = Move(1, 8)
        # returns Move(2, 6), i.e. this slice in b:
        # |-|-||--|
        #   xxxx
        m.strip_on(b)
        """
        if board.a_stick not in board[self.left:self.right]:
            return None
        new_left = self.left
        while board[new_left] == board.a_gap:
            new_left += 1
        new_right = self.right
        while board[new_right - 1] == board.a_gap:
            new_right -= 1
        return __class__(new_left, new_right)


class Player:
    """Attributes:
    - name: a string
    - action: a function that takes a Player and a Game, and returns the Move
      that the player wishes to play on the Game’s Board.
    """
    # TODO type annotation of action_function
    def __init__(self, name, action_function):
        self.name = name
        self.action = action_function

    def ask_move(self, game):
        return self.action(self, game)


class Settings:
    """A class to hold the different settings that define a game and that can
    vary from game to game. Attributes:
    - board_size
    - max_take
    """
    def __init__(self, board_size, max_take):
        self.board_size = board_size
        self.max_take = max_take


class Game:
    """Attributes:
    - players: a couple (or list of length 2) containing two Player instances.
    - settings: contains the board size and the maximum number of sticks a
      player may take on his turn.
    """
    # TODO type annotate players. How to specify list length?
    def __init__(self, players, settings):
        self.players = players
        self.settings = settings
        self.board = Board(settings.board_size)

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
            move = player.ask_move(self)
            # the interface is responsible for only providing legal moves
            self.board.play_move(move)
            # switch player for next turn
            current_player = 1 - current_player
