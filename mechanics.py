"""Common module for the Sticky-Nim game
    Describes the Board, Move, Player, Settings and Game classes.
"""


from collections import Sequence


class Board(Sequence):
    """The class describing a physical board. A board is a rectangle containing
    a line of slots. Each slot contains a stick at first. During a game, players
    take turns removing some of the sticks, leaving empty slots on the board
    called gaps.
    """

    _DEFAULT_STICK_CHAR = '|'
    _DEFAULT_GAP_CHAR = '-'

    # Text representation of sticks and gaps, used when printing Boards.
    # They can only be one character long
    stick_char = _DEFAULT_STICK_CHAR
    gap_char = _DEFAULT_GAP_CHAR

    def __init__(self, size, slots=None, a_stick=None, a_gap=None):
        """Arguments:
        @a_stick: internal value representing a stick on the board.
        @a_gap: internal value representing an empty slot on the board.
        @slots: the contents of the board. A list containing only sticks or gaps
        (i.e. instances of a_stick or a_gap).
        """
        if a_stick is None:
            a_stick = 1
        if a_gap is None:
            a_gap = 0
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
        if not isinstance(slots, list):
            raise TypeError(f"list was expected, got {type(slots)}")
        return cls(len(slots), slots, a_stick, a_gap)

    @classmethod
    def from_string(cls, string, a_stick=None, a_gap=None):
        """Creates and returns a Board from its string representation, for
        instance "|--|-||-||".
        @string should only contain a_stick and/or a_gap. If they’re not
        specified, @string should only contain cls.stick_char and/or
        cls.gap_char.
        """
        if not isinstance(string, str):
            raise TypeError(f"str was expected, got {type(string)}")
        if a_stick is None:
            a_stick = cls.stick_char
        if a_gap is None:
            a_gap = cls.gap_char
        return cls(len(string), list(string), a_stick, a_gap)

    def __repr__(self):
        return f"{self._slots} (sticks: {self.a_stick}, gaps: {self.a_gap})"

    def __str__(self):
        """Example typical board representation:
        ||-|||--|
        where '|' are sticks and '-' are gaps.
        """
        board = []
        for s in self._slots:
            if s == self.a_stick:
                board.append(self.stick_char)
            elif s == self.a_gap:
                board.append(self.gap_char)
            else:
                raise ValueError("Board contains unknown value "
                                 f"{str(s)} instead of {str(self.a_stick)} "
                                 f"or {str(self.a_gap)}")
        return ''.join(board)

    def __eq__(self, other):
        """Returns True if the specified Boards are the same length and contain
        sticks and gaps at the same spots, i.e. if they have the same string
        representation."""
        return str(self) == str(other)

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
        """Returns the number of sticks that this Board can contain."""
        return len(self._slots)

    def reset(self):
        """Fills this Board with sticks, making it ready for a new game."""
        for i in range(len(self._slots)):
            self._slots[i] = self.a_stick

    def is_empty(self):
        """Returns True if this Board only contains gaps. Typically called to
        check whether a game has ended."""
        return self.a_stick not in self._slots

    def _process(self):
        """Computes and returns to_config() and to_groups() as a duple.
        See to_config() and to_groups() below."""
        config = []
        groups = []
        group_size = 0
        group_start = 0
        # Adding an extra slot at the end of the board avoids duplicated code
        # after the for loop below
        extended_board = __class__.from_string(str(self) + Board.gap_char)
        for i, slot in enumerate(extended_board):
            if slot == extended_board.a_stick:
                if group_size == 0:
                    group_start = i
                group_size += 1
            else:
                if group_size > 0:  # we've reached the end of a group of sticks
                    config.append(group_size)
                    groups.append((group_start, group_size))
                    group_size = 0
        config.sort(reverse=True)
        return config, groups

    def to_config(self):
        """Returns the configuration (see the readme) that summarizes this
        Board."""
        return self._process()[0]

    def to_groups(self):
        """Returns a list of couples (group_start_index, group_size) that
        describes this Board.
        Examples:
        Board       Returned list
        ||||||||||  [(0, 10)] (a group of 10 sticks starting at index 0)
        |||-||||||  [(0, 3), (4, 6)]
        |||-|---||  [(0, 3), (4, 1), (8, 2)]
        --|-|---||  [(2, 1), (4, 1), (8, 2)]
        """
        return self._process()[1]

    def list_moves(self, take, group_size, offset=0):
        """Returns the (possibly empty) list of all Moves on this Board that
        remove @take sticks in a group of @group_size sticks, leaving @offset
        sticks at the edge of said group.
        Example:
        With a board b represented by '|||-|||||-', calling
        b.list_moves(2, 5, 1) means we want to find moves that take 2 sticks,
        one stick away from the edge of a 5-stick group.
        Returned list: [Move(5, 7), Move(6, 8)]
        Play Move(5, 7) and the Board becomes '|||-|--||-', or
        play Move(6, 8) and the Board becomes '|||-||--|-'.
        """
        if take + offset > group_size:
            return None
        groups = self.to_groups()
        fitting_moves = []
        for i_start, size in groups:
            if size == group_size:
                take_starts = [i_start + offset, i_start + size - offset - take]
                for i in set(take_starts):  # set removes a possible duplicate
                    fitting_moves.append(Move(i, i + take))
        return fitting_moves

    def play_move(self, move):
        """Plays the specified move, i.e. removes all the sticks in the slice
        [move.left:move.right] of this Board.
        Returns True if the slice contained only sticks (the move was probably
        legal), False if there were any gaps in the slice (the move was
        definitely illegal).
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
    For some Move m and some Board b, b[m.left:m.right] or simply b[m] is the
    slice of b where sticks are to be taken from (that is, from b[m.left]
    included, to b[m.right - 1] included).

    left should always be less than right. Using negative indices may result in
    undefined behavior.
    """
    def __init__(self, index_1, index_2):
        self.left = min(index_1, index_2)
        self.right = max(index_1, index_2)

    def __repr__(self):
        """A Move is represented in a way similar to how slices are used. For
        instance, a Move with attributes left = 4 and right = 6 is printed as
        '[4:6]'.
        """
        return f"[{self.left}:{self.right}]"

    def __len__(self):
        """Returns the number of sticks that this Move would remove on an
        (infinitely long) board filled with sticks.
        """
        return self.right - self.left

    def __eq__(self, other):
        """Returns True if both Moves have the same left and right attributes,
        or if they are both None."""
        if self is None:
            return other is None
        else:
            return other is not None \
                and self.left == other.left and self.right == other.right

    def is_out_of_bounds_on(self, board):
        """Returns True if this Move’s indices are out of the specified Board’s
        boundaries.
        Example:
        Board b: |||| (length 4)
        Move m1: [2:4]
        Move m2: [2:5]
        m1 is legal on b, but m2 is out of bounds.
        """
        return self.left < 0 or self.right > len(board)

    def contains_gap_on(self, board):
        """Returns True if the slice of the specified Board contains a gap."""
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
        m = Move(1, 8)
        # m is about this slice of b:
        # |-|-||--|
        #  xxxxxxx
        m.strip_on(b)
        # returns Move(2, 6), i.e. this slice in b:
        # |-|-||--|
        #   xxxx
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
            # the interface is responsible for providing legal moves only
            self.board.play_move(move)
            # switch player for next turn
            current_player = 1 - current_player
