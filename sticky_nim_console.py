"""Sticky Nim - Console version

    This game is a variant of the game of Nim.
    Rules:
    - 2 players
    - Start with a line of sticks: ||||||||||
    - On their turn, a player may take up to 3 sticks from the line. These
      sticks need to be next to each other.
    - Whoever takes the last stick loses.

    The starting quantity of sticks and the number of sticks you are allowed
    to take every turn can be customized.

    Example game starting with 10 sticks and up to 3 sticks taken per turn:
    =====================================================================
    Player   Action                          Board
    =====================================================================
             (Starting position)             ||||||||||
       1     Takes one stick                 |||-||||||
       2     Takes three sticks              |||-|---||
       1     Takes two sticks                |---|---||
       2     Takes one stick                 |---|---|-
       1     Can only take one stick         |---|-----
       2     Doesn't have a choice either    ----|-----
       1     Has to take the last one...     ----------
    =====================================================================
    So Player 1 loses.

    Example illegal move:
    Say the board looks like this:     |||-|-||||
    You cannot take these two sticks:  |||-x-x|||
    Because they are not next to each other.
"""

# TODO
# - translate everything to English
# - commentaires de documentation
# - déplacer les fonctions d'interface vers un autre fichier, pour pouvoir
#   facilement créer plusieurs interfaces ?
# - interface graphique avec pygame ? PyQt ?
# - utiliser un dictionary pour la liste de tuples (commande, fonction associée,
#   description) pour que les fonctions display_help, human_action et menu
#   soient générées plus automatiquement
#

import sys
import random

from mechanics import Board, Move, Player, Game
import ai

DEFAULT_BOARD_SIZE = 20
DEFAULT_MAX_TAKE = 3
# Taille à partir de laquelle on avertit l'utilisateur qu'utiiser une IA peut
# nécéssiter un long temps de chargement
LARGE_BOARD_WARNING = 27

_settings = {
    'board_size': -1,
    'max_take': -1,
    'screen_width': 80  # TODO paramétrable par l'utilisateur ? auto-ajustable ?
}

# Typiquement, le plateau contiendra une vingtaine de bâtons.
# Cette interface est limitée à 62 (2*26 + 10) bâtons.
# Ce devrait être plus que suffisant, le jeu n'a pas spécialement plus
# d'intérêt quand on agrandit le plateau.
_coordinates = [chr(i) for i in range(ord('a'), ord('z') + 1)] \
    + [chr(i) for i in range(ord('A'), ord('Z') + 1)] \
    + [chr(i) for i in range(ord('0'), ord('9') + 1)]


class PleaseRestart(Exception):
    pass


class PleaseStop(Exception):
    pass


class PleaseExit(Exception):
    pass


def display_rules():
    print(" Jeu du bâton : règles ".center(_settings['screen_width'], '-'))
    print('''    - 2 joueurs
    - Au départ, on a des bâtons alignés : ||||||||||
    - Chacun à son tour, un joueur prend 1, 2, ou 3 bâtons, où il veut,
      mais les bâtons qu'il prend doivent être adjacents.
    - Celui qui prend le dernier bâton a perdu.

    Le nombre de bâtons au départ est modifiable, ainsi que la limite de
    3 bâtons par tour.

    Exemple de partie avec 10 bâtons et prise maximale de 3 bâtons :
    ========================================================
    Joueur   Action                            Plateau
    ========================================================
             (Position de départ)              ||||||||||
       1     Prend un bâton                    |||-||||||
       2     Prend trois bâtons                |||-|---||
       1     Prend deux bâtons                 |---|---||
       2     Prend un bâton                    |---|---|-
       1     Ne peut prendre qu'un bâton       |---|-----
       2     N'a pas le choix non plus         ----|-----
       1     Obligé de prendre le dernier...   ----------
    ========================================================
    ... et donc le joueur 1 a perdu.

    ''')
    print("Paramètres actuels")
    print("    - Bâtons au départ :", _settings['board_size'])
    print("    - Prise maximale   :", _settings['max_take'], "bâtons par tour")


def display_help():
    '''Affiche la liste des commandes disponibles.
    '''
    print(" Jeu du bâton : aide ".center(_settings['screen_width'], '-'))
    print("Commandes générales :")
    print("    new      Nouvelle partie")
    print("    settings Changer les paramètres du jeu")
    print("    rules    Afficher les règles du jeu")
    print("    help     Afficher cette aide")
    print("    quit     Quitter")
    print("Commandes en partie :")
    print("    xy       Prendre les bâtons entre les positions x et y")
    print("    aff      Réafficher le plateau")
    print("    menu     Retourner au menu (arrête la partie en cours)")
    # additional purposefully undocumented game command : "cheat"


def display_board(board):
    '''Affiche le plateau de jeu sous la forme suivante :

    < | | - | | | | - - | | | | | | | - - - | >
      a b   d e f g     j k l m n o p       t

    Les '|' sont les bâtons, les '-' sont les cases vides.
    Si le plateau est trop large, l'espace entre chaque case est supprimée.
    '''
    sticks = ['<']
    letters = [' ']
    for i, slot in enumerate(board):
        if slot == board.a_stick:
            sticks.append('|')
            letters.append(_coordinates[i])
        else:  # slot == board.a_gap:
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
    while True:
        s = input(prompt).strip()
        if s != "":
            return s


def confirm(message, yes="O", no="n"):
    '''Affiche le message spécifié, et lit une entrée console. Si c'est yes,
    renvoie True, si c'est no, renvoie False. Si c'est autre chose, renvoie
    quand même False, mais affiche en plus un message.
    Utilisation typique :
    if confirm("Continuer ?"):
        # Code si l'utilisateur a tapé "O"
    else:
        # Code si l'utilisateur a tapé autre chose
    '''
    print(message + " (" + yes + "/" + no + ") ", end='')
    choice = really_input()
    if choice == yes:
        return True
    else:
        if choice != no:
            print("Je prends ça pour un non :)")
        return False


def to_action(move):
    '''Renvoie la chaine que l'humain devrait taper s'il voulait jouer le coup
    spécifié.'''
    action = _coordinates[move.left]
    if move.size() > 1:
        action += _coordinates[move.right - 1]
    return action


def cheat(board):
    # Print all winning moves if any
    # (Only works if the AI module knows about the current configuration)
    config = ai._to_config(board)
    if config[0] == 1:
        if len(config) == 1:
            print("Vraiment ?")
        else:
            print("Ben, y'a pas vraiment le choix là...")
        return
    if ai.loading_needed(_settings['board_size'], _settings['max_take']):
        # Le module d'ia aurait besoin de faire des calculs supplémentaires
        # avant de connaître la réponse
        print("Mais j'en sais rien moi !")
        return
    solutions = ai._winning_moves(config)
    if solutions == []:
        messages = [
            "Là je vais pas pouvoir t'aider...",
            "Laisse tomber, ton adversaire est trop fort",
            "Je vois pas...",
            ]
        print(random.choice(messages))
    else:
        moves = []
        for target in solutions:
            take, group, offset = ai._move_between(config, target)
            moves.append(ai._build_move(board, take, group, offset))
        print(', '.join(sorted([to_action(m) for m in moves])))


def human_action(player, board):
    '''Renvoie le coup que le joueur humain spécifié souhaite jouer sur le
    plateau spécifé.
    Permet à l'humain d'exécuter d'autres commandes avant de jouer (afficher
    l'aide, les règles, arrêter la partie, etc.)
    '''
    display_board(board)
    while True:
        action = really_input(player.name + "> ")
        if action == "menu":
            if confirm("Arrêter cette partie ?"):
                raise PleaseStop()
        elif action == "new":
            if confirm("Recommencer cette partie ?"):
                raise PleaseRestart()
        elif action == "quit":
            if confirm("Quitter le jeu ?"):
                raise PleaseExit()
        elif action == "settings":
            print("Hmm, il faudrait d'abord quitter la partie pour cela")
        elif action == "rules":
            display_rules()
        elif action == "help":
            display_help()
        elif action == "aff":
            display_board(board)
        elif action == "cheat":
            # (This command does not show in the help)
            cheat(board)
        elif len(action) <= 2 \
                and action[0] in _coordinates \
                and action[-1] in _coordinates:
            # conversion de l'action en un couple d'indices
            end1 = _coordinates.index(action[0])
            end2 = _coordinates.index(action[-1])
            # using min and max allows the user to enter coordinates from
            # right to left
            move = Move(min(end1, end2), max(end1, end2) + 1)
            # checking move legality
            if move.is_out_of_bounds_on(board):
                print("Ce coup me paraît hors limites")
            elif move.is_too_large_on(board):
                print("Prenez", board.max_take, "bâtons, pas plus !")
            elif move.contains_gap_on(board):
                print("Coup impossible")
            else:
                return move
        else:
            print("Je n'ai pas compris")


def computer_action(player, board):
    '''Renvoie le coup que le joueur artificiel souhaite jouer sur le plateau
    spécifé.
    Affiche l'éventuel message que ce joueur souhaite faire passer à l'écran,
    ainsi que le coup joué.
    '''
    display_board(board)
    print(player.name + "> ", end='')
    move, message = ai.generate_move(board)
    if not move.is_legal_on(board):
        raise Exception("Coup incorrect de la part de l'IA : " + str(move))
    if message != "":
        print(message, end=' ')
    print(to_action(move))
    return move


def change_settings():
    '''Makes the user input new settings for future games.'''
    while True:
        print("Taille du plateau ?", end=' ')
        try:
            board_size = int(really_input())
        except:
            print("Je n'ai pas compris")
            continue
        if board_size <= 0:
            print("C'est un peu petit non?")
        elif board_size > len(_coordinates):
            print("Désolé, je suis limité à",
                  len(_coordinates), "bâtons sur le plateau")
        else:
            _settings["board_size"] = board_size
            break
    while True:
        print("Prise maximale par tour ?", end=' ')
        try:
            max_take = int(really_input())
        except:
            print("Je n'ai pas compris")
            continue
        if max_take <= 0:
            print("Hmm, des bâtons négatifs... Trop compliqué pour moi")
        else:
            _settings['max_take'] = max_take
            break


def choose_players():
    '''Demande à l'utilisateur de choisir si les joueurs seront humains
    ou ordinateurs.
    Renvoie une liste de deux Player.
    '''
    players = []
    p = 0
    while p < 2:
        print("Joueur", p + 1, ": humain ou ordinateur ? (h/o)", end=' ')
        s = really_input()
        if s == 'o':
            if ai.loading_needed(_settings['board_size'],
                                 _settings['max_take']):
                if _settings['board_size'] > LARGE_BOARD_WARNING:
                    print("Attention, le plateau est grand, il risque d'y "
                          "avoir un long temps de chargement." )
                    if not confirm("Continuer ?"):
                        continue
                print("Chargement...")
            ai.initialize(_settings['board_size'], _settings['max_take'])
            players.append(Player("Ordinateur " + str(p + 1), computer_action))
        else:
            if s != 'h':
                print("Bien tenté, ce sera humain alors")
            players.append(Player("Joueur " + str(p + 1), human_action))
        p += 1
    return players


def new_game(players):
    '''Fait jouer une partie aux joueurs spécifiés (players est une liste de
    deux Player).
    Renvoie True si les joueurs souhaitent refaire immédiatement une partie,
    False sinon.
    '''
    game = Game(
        players,
        _settings['board_size'],
        _settings['max_take'])
    try:
        winner = game.play()
        print(' '.join([winner.name, "a gagné !"])
              .center(_settings['screen_width']))
    except PleaseRestart:
        return True
    except PleaseStop:
        return False
    else:   # the game ended normally
        return confirm("Refaire une partie ?")


def menu(width):
    while True:
        action = really_input("menu> ")
        if action in ["menu", "m"]:
            pass
        elif action == "aff":
            print("Hmm, il n'y a aucune partie en cours")
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
            while True:
                print(" Nouvelle partie ".center(width, '-'))
                restart = new_game(players)
                if not restart:
                    break
            print("-" * width)
        else:
            print("Je n'ai pas compris")


def parse_command_line():
    # TODO finer exception handling?
    try:
        size = int(sys.argv[1])
    except:
        size = DEFAULT_BOARD_SIZE
    if size <= 0:
        print("Hmm, la taille du plateau doit être positive")
        quit()
    if size > len(_coordinates):
        print("Désolé, cette interface est limitée à",
              len(_coordinates), "bâtons sur le plateau")
        quit()
    _settings['board_size'] = size

    try:
        max_take = int(sys.argv[2])
    except:
        max_take = DEFAULT_MAX_TAKE
    if max_take <= 0:
        print("Hmm, le nombre maximal de bâtons à prendre doit être positif")
        quit()
    _settings['max_take'] = max_take


# ============================ Programme principal ============================


if __name__ == "__main__":
    parse_command_line()
    width = _settings['screen_width']

    print(" Jeu du bâton ".center(width, '='))
    print("Tapez help pour afficher l'aide")
    try:
        menu(width)
    except PleaseExit:
        pass
    print(" Jeu du bâton ==== À bientôt ! ".center(width, '='))
