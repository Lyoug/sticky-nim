'''Module d'intelligence artificielle pour le jeu du bâton

    Exemple de partie avec 10 bâtons et prise maximale de 3 bâtons :
    =====================================================================
    Joueur   Action                          Plateau
    =====================================================================
             (Position de départ)            ||||||||||
       1     Prend un bâton                  |||-||||||
       2     Prend trois bâtons              |||-|---||
       1     Prend deux bâtons               |---|---||
       2     Prend un bâton                  |---|---|-
       1     Ne peut prendre qu'un bâton     |---|-----
       2     N'a pas le choix non plus       ----|-----
       1     Obligé de prendre le dernier... ----------
    =====================================================================
    Et donc le joueur 1 a perdu.

    Définitions/Notations :
    - Configuration : une liste d'entiers (décroissants) qui décrit une
      situation de jeu.
      Par exemple, la partie montrée ci-dessus contient, dans l'ordre,
      les configurations :
      [10], [6, 3], [3, 2, 1], [2, 1, 1], [1, 1, 1], [1, 1], [1], []
    - Configuration perdante (CP) :  une configuration telle que si un
      joueur s'y trouve et que c'est son tour de jouer, il ne pourra
      jamais gagner quoi qu'il fasse (du moins, à condition que son
      adversaire joue correctement).
      Exemple : [2, 2] est perdante : si c'est mon tour, je n'ai que deux
      coups possibles :
      - si je prends un bâton, mon adversaire, qui voit [2, 1], en prend
        deux, puis il ne me reste que le dernier.
      - si je prends deux bâtons, mon adversaire, qui voit [2], en prend
        un, et il ne me reste que le dernier.
      Dans tous les cas j'ai perdu.

    L'idée, pour être sûr de gagner, est de jouer un coup qui place
    l'adversaire dans une configuration perdante (CP). L'intelligence
    artificielle construit donc au départ la liste de toutes les CP, puis
    quand on lui demande de jouer un coup, cherche s'il est possible
    d'atteindre une CP depuis le plateau courant. Si oui, on joue un tel
    coup, sinon, on en génère un au hasard.
'''

# TODO
# - test du module plus propre, plus exhaustif, plus automatique
# - différents niveaux de difficulté ? i.e :
#   - parfait : ne peut perdre que contre un autre joueur parfait (c'est le
#     niveau actuel)
#   - ... niveaux intermédiaires ? cherche à obtenir une config symétrique ?
#   - aléatoire

import random
from mechanics import Board, Move

# Interface avec l'extérieur :
# - initialize permet à l'appelant de spécifier la taille du plateau et le
#   nombre maximal de bâtons que l'on peut prendre à la fois. Doit être appelée
#   avant de pouvoir générer des coups.
# - laoding_needed renvoie True si un appel à initialize avec les mêmes
#   paramètres nécessiterait des calculs supplémentaires.
# - generate_move prend en entrée un Board, et renvoie un couple contenant :
#   - un Move
#   - un éventuel message (une chaine) destiné à l'interface utilisateur
__all__ = ["initialize", "loading_needed", "generate_move"]

# Contient les paramètres du module.
# Ils sont réglés lors des appels à initialize(board_size, max_take)
_settings = {
    'board_size': 0,  # taille du plateau
    'max_take': 0,    # nombre maximal de bâtons qu'on peut prendre en un coup
}


# ===================== Fonctions liées au plateau de jeu =====================


def _process(board):
    '''Voir _to_configs() et _to_groups().
    '''
    config = []
    groups = []
    group_size = 0
    group_start = 0
    # Astuce pour prendre en compte le dernier groupe sans code supplémentaire
    # après la boucle : on ajoute un case vide à la fin du plateau
    extended_board = Board.from_list(board.slots + [board.a_gap],
                                     board.a_gap,
                                     board.a_stick)
    for i, slot in enumerate(extended_board):
        if slot == board.a_stick:
            if group_size == 0:
                group_start = i
            group_size += 1
        else:  # slot == board.a_gap:
            # if we've reached the end of a group of sticks
            if group_size > 0:
                config.append(group_size)
                groups.append((group_start, group_size))
                group_size = 0
    config.sort(reverse=True)
    return config, groups


def _to_config(board):
    '''Renvoie la configuration qui décrit le plateau spécifié.
    '''
    return _process(board)[0]


def _to_groups(board):
    '''Renvoie une description du plateau spécifié, sous la forme d'une
    liste de couples (indice_de_debut_de_groupe, taille_du_groupe).
    '''
    return _process(board)[1]


def _build_move(board, take, group_size, offset=0):
    '''Renvoie un coup qui consiste à prendre take bâtons dans un
    groupe de group_size bâtons, en laissant offset bâtons au bord du
    groupe.
    Si un tel coup n'existe pas sur le plateau spécifié, renvoie None.
    '''
    if take + offset > group_size:
        return None
    groups = _to_groups(board)
    for i_start, size in groups:
        if size == group_size:
            left = i_start + offset
            right = left + take
            return Move(left, right)
    else:  # on n'a trouvé aucun groupe de la bonne taille sur le plateau
        return None


# ===================== Fonctions liées au configurations =====================

# Table de toutes les configurations possibles
# _configs[n] = tableau des configs à n bâtons
# _configs[n][k] = liste des configs à n bâtons divisés en k groupes
# _configs[n][k][i] = i-ième config à n bâtons et k groupes
_configs = []
_configs.append([])   # liste (vide) des configs à 0 bâtons

# Liste des configurations perdantes
_losing_configs = []

# Dictionnaire pour sauvegarder les configs perdantes construites avec
# différents max_take
_losing_backup = {}


def _move_exists(config_from, config_to, max_take):
    '''Renvoie True si, dans la situation config_from, on peut jouer un coup
    qui amène à la situation config_to en prenant au plus max_take bâtons.
    '''
    # Après un coup, le nombre de groupes peut soit :
    # - être inchangé,
    # - diminuer de un (si on prend les derniers bâtons d'un groupe),
    # - augmenter de un (si on divise en deux un groupe, en prenant des bâtons
    #   au milieu)
    if abs(len(config_from) - len(config_to)) > 1:
        return False

    # On doit prendre entre 1 et prise_max bâtons par coup
    take = sum(config_from) - sum(config_to)
    if take < 1 or take > max_take:
        return False

    # Comme on ne peut toucher qu'à un groupe en jouant, si on enlève de
    # config_from tous les éléments que config_from et config_to ont en commun,
    c_from = config_from[:]
    for group in config_to:
        if group in c_from:
            c_from.remove(group)
    # ... il ne doit alors rester qu'un seul groupe dans c_from (celui auquel
    # le joueur enlève des bâtons)
    return len(c_from) == 1


def _move_between(config_from, config_to):
    '''Renvoie un triplet d'entiers qui décrit l'action à effectuer pour
    passer de config_from à config_to :
    - le nombre de bâtons à prendre
    - la taille du groupe auquel il faut prendre des bâtons
    - le nombre de bâtons qu'il faut laisser au bord du groupe
    S'il n'existe pas de coup entre les deux config, renvoie None.
    '''
    take = sum(config_from) - sum(config_to)
    if not _move_exists(config_from, config_to, take):
        return None
    # suppression des groupes communs aux deux configs
    c_from = config_from[:]
    c_to = config_to[:]
    for group in config_to:
        if group in c_from:
            c_from.remove(group)
            c_to.remove(group)
    # il ne reste forcément qu'un groupe dans c_from
    group_to_take_from = c_from[0]
    # il peut rester dans c_to :
    # - 0 groupes : on a pris tout le groupe de c_from
    # - 1 groupe  : on a pris les bâtons au bord du groupe
    # - 2 groupes : on a pris les bâtons au milieu du groupe
    if len(c_to) <= 1:
        offset = 0
    else:  # len(c_to) == 2
        # on pourrait aussi prendre c_to[1], on obtiendrait simplement un
        # décalage symétrique
        offset = c_to[0]
    return take, group_to_take_from, offset


def _reachable(config_from, max_take, configs_to=None):
    '''Renvoie la liste de toutes les configurations possibles (parmi la
    liste configs_to si elle est spécifiée) qui peuvent être atteintes
    en un coup depuis config_from.
    '''
    if configs_to is not None:
        return [c for c in configs_to
                if _move_exists(config_from, c, max_take)]
    else:
        # TODO Générer toutes les configs atteignables depuis config_from
        return []


def _build_configs(up_to, start_from=1):
    '''Remplit la table de toutes les configurations contenant up_to bâtons
    et moins.
    '''
    global _configs
    for n in range(start_from, up_to + 1):
        # Création des configs à n bâtons
        _configs.append([])          # initialisation
        _configs[n].append([])       # aucune config à 0 groupes
        _configs[n].append([[n]])    # unique config à 1 groupe
        for k in range(2, n + 1):
            # Création de la liste des configs à n bâtons et k groupes
            # Ces configs sont séparées en deux ensembles (disjoints) :
            # A. les configs à n-1 bâtons en k-1 groupes,
            #    auxquelles on va ajouter un groupe de 1 bâton
            # B. les configs à n-k bâtons en k groupes,
            #    dans lesquelles on va ajouter 1 bâton à chaque groupe
            _configs[n].append([])       # initialisation

            # Ensemble A
            new_configs = []
            for c in _configs[n - 1][k - 1]:     # copie profonde
                new_configs.append(c[:])
            for c in new_configs:
                c.append(1)     # ajout du nouveau groupe de 1 bâton
            _configs[n][k].extend(new_configs)

            # Ensemble B
            if k > n - k:
                continue
            new_configs = []
            for c in _configs[n - k][k]:         # copie profonde
                new_configs.append(c[:])
            # ajout d'un bâton à chaque groupe de chaque config
            new_configs = [[x + 1 for x in c] for c in new_configs]
            _configs[n][k].extend(new_configs)


# Fonction la plus lente. Sur mon ordi (Core 2 Duo de 2009) :
# - Pour ~20 bâtons, met une petite seconde
# - Pour ~30 batons, met une petite minute
# - Pour ~40 batons, met une petite heure
def _build_losing_configs(up_to, max_take, start_from=1):
    '''Construit la liste de toutes les configurations perdantes à
    up_to bâtons ou moins.

    Nécessite que la table des configurations ait été créée (avec
    _build_configs()), au moins jusqu'à up_to.
    '''

    # Pour toutes les configs de board_size bâtons au plus, on parcourt la
    # liste des configurations perdantes connues, à la recherche d'une CP qui
    # peut être atteinte depuis la config courante.
    # Si on n'en a trouvé aucune, c'est que cette config est perdante : on
    # l'ajoute à la liste
    global _losing_configs
    for n in range(start_from, up_to + 1):
        # raccourci : pour n impair, aucune config n'est perdante sauf celle
        # constituée uniquement de 1
        if n % 2 == 1:
            _losing_configs.append([1] * n)
            continue
        for k in range(1, n + 1):
            for config in _configs[n][k]:
                for lc in _losing_configs:
                    if _move_exists(config, lc, max_take):
                        break
                else:  # nobreak
                    _losing_configs.append(config)


def _winning_moves(config):
    return _reachable(config, _settings['max_take'], _losing_configs)


def _message_about(config):
    '''Renvoie un message à propos d'une configuration supposée perdante.
    '''

    # s'il ne reste que le dernier bâton (= fin de la partie)
    if config == [1]:
        messages = [
            "Je m'incline !",
            "Bien joué !",
            "Bravo !",
        ]
    # s'il ne reste qu'un nombre impair de groupes de 1 (= défaite obligatoire)
    elif config[0] == 1 and sum(config) % 2 == 1:
        messages = [
            "Je suis mal barré...",
            "Ça sent la fin...",
            "Aïe aïe aïe...",
        ]
    # cas général : défaite à moins que l'adversaire fasse une erreur
    else:
        messages = [
            "Hmm...",
            "J'hésite...",
            "Pas facile...",
            "Pas mal...",
        ]
        # messages supplémentaires si on approche de la fin de la partie
        if sum(config) <= _settings['board_size'] / 3:
            messages.extend([
                "Vous êtes fort, on dirait !",
                "Eh bien, voilà un adversaire de taille !",
                "Décidément...",
            ])
    return random.choice(messages)


# =========================== Fonctions principales ===========================


def initialize(board_size, max_take):
    '''Fonction à appeler avant de pouvoir appeler la génération de coup.
    '''
    global _configs
    global _losing_configs
    # fetch possible backed up data
    known_size, _losing_configs = \
        _losing_backup[max_take] if max_take in _losing_backup else (0, [])

    _settings['board_size'] = board_size
    _settings['max_take'] = max_take
    _build_configs(up_to=board_size, start_from=len(_configs))
    _build_losing_configs(board_size, max_take, start_from=known_size + 1)
    # if we've built new things, back them up
    if loading_needed(board_size, max_take):
        _losing_backup[max_take] = (board_size, _losing_configs)


def loading_needed(board_size, max_take):
    '''Renvoie True si un appel à initialize avec ces paramètres nécessiterait
    des calculs supplémentaires.
    '''
    return max_take not in _losing_backup \
        or board_size > _losing_backup[max_take][0]


def generate_move(board):
    '''Renvoie un Move (~= un couple d'entiers, indices entre
    lesquels l'IA souhaite enlever des bâtons) et un message destiné à
    l'interface.
    Nécessite que la fonction initialize ait déjà été appelée.
    '''
    config = _to_config(board)
    solutions = _winning_moves(config)
    if solutions is None:
        raise Exception(
            "Plateau non étudié. Il y a probablement eu une erreur à "
            "l'initialisation du module " + __name__)
    elif solutions:
        # on construit le coup à jouer pour aller vers une des solutions
        take, group, offset = _move_between(config, random.choice(solutions))
        message = ""
    else:
        # La configuration est perdante ; on va générer un coup au hasard.

        # TODO générer le coup le "plus compliqué" possible ?
        # "plus compliqué" au sens : qui met l'adversaire dans une config qui
        # ait le moins de coups gagnants possibles

        # choix du groupe à toucher,
        # du nombre de bâtons à prendre dans ce groupe,
        # puis du nombre de bâtons à laisser au bord du groupe
        group = random.choice(config)
        take = random.randint(1, min(_settings['max_take'], group))
        offset = random.randint(0, group - take)
        message = _message_about(config)
    return _build_move(board, take, group, offset), message


# ============================== Test du module ===============================


def _to_board(config, board_size=None, shuffle=False):
    '''Renvoie un plateau correspondant à la config spécifiée :
    il contient tous les groupes de config, séparés par une case vide.

    Si board_size est spécifié, ajoute des cases vides à la fin (la droite)
    du plateau. Si board_size est trop petit pour contenir config, lève
    ValueError.
    Mettre shuffle à True si l'on veut que les groupes de configs soient
    mélangés au hasard (config ne sera pas modidfiée). Par défaut ils sont
    classés du plus grand au plus petit.
    '''
    # place nécessaire sur le plateau : tous les bâtons, plus des cases
    # vides pour séparer les groupes
    min_size = sum(config) + len(config) - 1
    if board_size is None:
        board_size = min_size
    elif board_size < min_size:
        raise ValueError(
            "La configuration "
            + str(config)
            + " ne rentre pas sur un plateau de taille "
            + str(board_size))
    # else: rien

    conf = config[:]
    if shuffle:
        random.shuffle(conf)

    slots = []
    gap = 0
    stick = 1
    for group in conf:
        slots.extend([stick] * group + [gap])
    # enlever le dernier empty que la boucle a mis en trop
    slots.pop()
    # ajouter les éventuelles cases vides supplémentaires
    slots.extend([gap] * (board_size - len(slots)))
    return Board.from_list(slots, gap, stick)


def _sizeof_configs():
    '''Renvoie le nombre de configurations stockées dans la table.
    '''
    n_configs = 0
    for n in range(1, len(_configs)):
        for k in range(1, n + 1):
            n_configs += len(_configs[n][k])
    return n_configs


def _composite(config1, config2):
    '''Renvoie une nouvelle configuration constituée des groupes de
    config1 et de config2.
    '''
    return sorted(config1 + config2, reverse=True)


def _contains(config, sub_config):
    '''Renvoie True si tous les groupes de sub_config font partie de
    config.
    '''
    for group in sub_config:
        if config.count(group) < sub_config.count(group):
            return False
    return True


def _prune_losing_configs():
    '''Renvoie la liste des configs perdantes privée de :
    - Celles qui terminent par une ou plusieurs paires de 1
    - Celles qui sont composées de plusieurs sous-configs perdantes
    '''
    pruned_losing_configs = []

    for c in _losing_configs:
        pruned = c[:]        # copie pour ne pas modifier losing_configs
        # les configs à 2 groupes ou moins sont toujours incluses
        if len(pruned) <= 2:
            pruned_losing_configs.append(pruned)
            continue
        # les configs ne contenant que des 1 sont ignorées
        if pruned[0] == 1:  # pruned[0] est le plus grand groupe. s'il vaut 1,
                            # tous les groupes de cette config valent 1
            continue

        # pour les autres configs, on commence par supprimer toutes les paires
        # de 1 finales
        n_1 = pruned.count(1)
        if n_1 > 1:
            to_remove = n_1 - n_1 % 2
            del pruned[-to_remove:]
        # puis on supprime toutes les sous-configs perdantes, à condition
        # que la config résulante reste perdante
        for lc in pruned_losing_configs[1:]:
            while _contains(pruned, lc):
                # tentative de suppression de lc
                without_lc = pruned[:]
                for group in lc:
                    without_lc.remove(group)
                # si le résultat reste perdant, on confirme la suppression
                if without_lc == [] or without_lc in _losing_configs:
                    pruned = without_lc
                else:       # without_lc est gagnante
                    break   # passer à la lc suivante
            if pruned == []:    # si on a déjà épuisé la config, pas la peine
                                # de continuer
                break
        # si on arrive ici et qu'il reste encore quelque chose dans
        # pruned, on l'ajoute à la liste
        if pruned != []:
            pruned_losing_configs.append(pruned)
    return pruned_losing_configs


if __name__ == "__main__":
    import sys
    import time

    # TODO Gestion plus fine des exceptions
    try:
        _settings['board_size'] = int(sys.argv[1])
    except:
        print("Usage :\n"
              "    python", sys.argv[0], "board_size [max_take]\n"
              "    if unspecified, max_take defaults to 3")
        quit()
    try:
        _settings['max_take'] = int(sys.argv[2])
    except:
        _settings['max_take'] = 3

    print("================== "
          "Jeu des bâtons / Test de l'IA "
          "==================")
    print("    Plateau        :", _settings['board_size'], "bâtons")
    print("    Prise maximale :", _settings['max_take'], "bâtons par tour")
    t = time.clock()
    initialize(_settings['board_size'], _settings['max_take'])
    t_init = round((time.clock() - t) * 1000, 1)  # millisecondes
    main_losing_configs = _prune_losing_configs()

    # print("------------------------- Configurations --------------------------")
    # for n in range(1, len(_configs)):
    #     print('-' * 10, n, "bâtons", '-' * 10)
    #     for k in range(1, n+1):
    #         lk = _configs[n][k]
    #         for config in lk:
    #             print(config, end = ' ')
    #         print()
    # print("-------------------- Configurations perdantes ---------------------")
    # for config in _losing_configs:
    #    print(config)
    print("-------------- Principales configurations perdantes --------------")
    for config in main_losing_configs:
        print(config)

    print("------------------------------------------------------------------")
    total = _sizeof_configs()
    losing = len(_losing_configs)
    print("Configurations possibles :", total)
    print("Configurations perdantes : ", losing,
          " (", round(losing / total * 100, 2), " %)",
          " (construites en ", t_init, " ms)",
          sep='')
    print("Configurations perdantes principales :", len(main_losing_configs))

    print("------------------------------------------------------------------")
    configs_test = [
        [_settings['board_size']],
        [3, 2, 1],
        [6, 5, 4, 4, 2, 1],
        [6, 5, 2, 1],
        [6, 4, 2],
        [5, 4, 1],
        [21, 1],
        [21, 5],
    ]
    configs_test.extend([[18 - n, n] for n in range(1, 10)])
    configs_test.extend([_composite([n, n], [5, 1]) for n in range(1, 11)])

    for config in configs_test:
        print(config, "->", end=' ')
        if sum(config) > _settings['board_size']:
            print("(inconnu)")
            continue
        solutions = _winning_moves(config)
        if solutions == []:
            print("perdu")
        else:
            print(solutions)

    print("------------------------------------------------------------------")
    boards_test = [Board.from_list(list(b), "o", "l") for b in [
        "",
        "o",
        "l",
        "ooooo",
        "lllll",
        "ollll",
        "llllo",
        "lolll",
        "lloll",
        "lolol",
    ]]
    print("Plateau / Config / Groupes")
    for board in boards_test:
        config, groups = _process(board)
        print(board, config, groups, sep=' / ')

    for config in configs_test:
        board = _to_board(config, shuffle=True)
        config_back = _to_config(board)
        if config_back != config:
            print("Conversion incorrecte :")
            print("    config départ  = ", config)
            print("    plateau = ", board)
            print("    config arrivée = ", config_back)

    print("==================================================================")
