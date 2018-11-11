#Sticky-Nim

This 2-player game is a variant of the [game of Nim](https://en.wikipedia.org/wiki/Nim).
- Start with a line of sticks: `< I I I I I I I I I I >`
- On your turn, you may take up to 3 sticks from the line, anywhere you want, but they need to be next to each other.
- Whoever takes the last stick loses.

#####Example game

|  Board                    | Player | Action                                       |   
| :-----------------------: | :----: | :------------------------------------------- | 
|   `a b c d e f g h i j`   |        |                                              |
| `< I I I I I I I I I I >` |   1    | Takes one stick, `d`                         |   
| `< I I I - I I I I I I >` |   2    | Takes three sticks, `fh`                     |   
| `< I I I - I - - - I I >` |   1    | Takes two sticks, `ab`                       |   
| `< - - I - I - - - I I >` |   2    | Takes one stick, `j`                         |   
| `< - - I - I - - - I - >` |   1    | Cannot take more than one stick, chooses `i` |   
| `< - - I - I - - - - - >` |   2    | Same, chooses `c`                            |   
| `< - - - - I - - - - - >` |   1    | Has to take the last one, `e`                |   
| `< - - - - - - - - - - >` |   2    | Wins                                         |


##Getting started

This game was written for Python 3.7 but uses nothing outside the standard library. To launch the game, open a console in the game directory and type:
```
python sticky_nim_console.py
```
(Make sure `python` points to a python 3 interpreter.) From then on, typing `help` will list all available commands.


## Features

- Play against a friend or against the computer (you can also watch two computers battle)
- Choose how many sticks to start with and how many you are allowed to take every turn


## Checklist

- [x] Translate everything to English
- [ ] Create different AI levels
- [ ] Rework the `ai_test` module
- [ ] Write tests for the `mechanics` module
- [ ] Add type annotations where needed
- [ ] Create a graphical interface


## Notations used in the source code

(No need to read this section unless you want to take a look at the source code.)

#### Configurations

In this project, a **configuration** is a list of decreasing integers, that summarizes a game situation. Each integer represents a group of adjacent sticks. Here are a few examples, using the example game shown above:

|  Board                    | Configuration |
| :-----------------------: | ------------- |
| `< I I I I I I I I I I >` | `[10]`        |
| `< I I I - I I I I I I >` | `[6, 3]`      |
| `< I I I - I - - - I I >` | `[3, 2, 1]`   |
| `< - - I - I - - - I I >` | `[2, 1, 1]`   |
| `< - - I - I - - - I - >` | `[1, 1, 1]`   |
| `< - - I - I - - - - - >` | `[1, 1]`      |
| `< - - - - I - - - - - >` | `[1]`         |
| `< - - - - - - - - - - >` | `[]`          |


An **n-stick k-group configuration** or **(n, k)-config** is a configuration made of n sticks total, that are divided into k groups. For instance, `[6, 3]` is a 9-stick 2-group
configuration. `[1, 1, 1]` is a (3, 3)-configuration: 3 sticks total, 3 groups.

#### Losing configurations

A **losing configuration** or **LC** is a configuration such that if it is my turn to play and I see this configuration on the board, I am bound to lose – provided that my opponent makes no mistake.
Some LC examples:
- `[1]`: If I see this on my turn, I can only take the last stick: I lose right away.
- `[1, 1, 1]`: I can only take one stick, leaving my opponent with `[1, 1]`. Then, they can only take one stick, leaving me with `[1]`. I lose.
- `[2, 2]`: I have two possible moves here:
  - If I take one stick (from any group of two), my opponent sees `[2, 1]`,
    takes the group of 2, and I am left with the last stick.
  - If I take two sticks, my opponent sees `[2]`, takes one stick from this
    last group, and leaves me with `[1]`.

  In both cases I lose, so `[2, 2]` is an LC.

It can be noted that any configuration that is not losing is a winning configuration.


## More info

Here are some pointers for more in depth information about the theory behind this game. I found out about all this mostly after I wrote most of the game, which explains why I may not have used the same notations as found in the literature.
- [Octal game](https://en.wikipedia.org/wiki/Octal_game): about some more Nim variants. Sticky-Nim is an octal game,  more specifically a generalisation of [Kayles](https://en.wikipedia.org/wiki/Kayles) and has an octal code of 0.777 when using default settings.
- [Integer partition](https://en.wikipedia.org/wiki/Partition_(number_theory)): details about what I called configurations.

