import json

# ============================================================
# UTILITAIRES
# ============================================================

def choisir_parmi(liste: list, label: str) -> str:
    """Affiche une liste numérotée et retourne le choix de l'utilisateur."""
    print(f"\n{label} :")
    for i, item in enumerate(liste, 1):
        print(f"  {i}. {item}")
    while True:
        choix = input("Choix (numéro) : ").strip()
        if choix.isdigit() and 1 <= int(choix) <= len(liste):
            return liste[int(choix) - 1]
        print("Choix invalide, réessayez.")


def trouver_as_du_routeur(intent: dict, nom_routeur: str) -> str | None:
    """Retourne le nom de l'AS contenant le routeur donné."""
    for nom_as, data_as in intent["AS"].items():
        if nom_routeur in data_as["routeurs"]:
            return nom_as
    return None


# ============================================================
# CREATION DE L'INTENT
# ============================================================

def creer_intent() -> dict:
    """Crée le squelette de base de l'intent."""
    intent = {
        "Plage_liens_inter": None,
        "AS": {}
    }
    print("\n=== Paramètres globaux ===")
    intent["Plage_liens_inter"] = input("Plage pour les liens inter-AS (ex: 10.0.0.0/24) : ").strip()
    return intent


# ============================================================
# GESTION DES AS
# ============================================================

def ajouter_as_provider(intent: dict):
    """Ajoute l'AS Provider."""
    print("\n=== AS Provider ===")

    if "Provider" in intent["AS"]:
        print("Un AS Provider existe déjà.")
        return

    bgp_as = int(input("Numéro d'AS BGP du Provider : ").strip())
    plage_loopbacks = input("Plage loopbacks (ex: 192.168.255.0/24) : ").strip()
    plage_liens = input("Plage liens internes (ex: 192.168.10.0/24) : ").strip()
    ospf_process = int(input("Numéro de process OSPF : ").strip())
    vrf = creer_vrfs()

    intent["AS"]["Provider"] = {
        "parametres_globaux": {
            "ospf_process": ospf_process,
            "plage_loopbacks": plage_loopbacks,
            "plage_liens": plage_liens,
            "bgp_as": bgp_as,
            "vrf": vrf
        },
        "routeurs": {}
    }
    print("AS Provider créé.")


def ajouter_as_client(intent: dict):
    """
    Ajoute un AS client (ex: Client1_1, Client1_2...).
    Un client peut avoir plusieurs sites, chacun étant un AS séparé.
    """
    print("\n=== Nouvel AS Client ===")
    nom_as = input("Nom de l'AS client (ex: Client1_1, Client2_1, ...) : ").strip()

    if nom_as in intent["AS"]:
        print(f"L'AS '{nom_as}' existe déjà.")
        return

    bgp_as = int(input("Numéro d'AS BGP : ").strip())
    plage_loopbacks = input("Plage loopbacks (ex: 192.145.255.0/24) : ").strip()
    plage_liens = input("Plage liens internes (ex: 192.145.10.0/24) : ").strip()

    intent["AS"][nom_as] = {
        "parametres_globaux": {
            "ospf_process": None,
            "plage_loopbacks": plage_loopbacks,
            "plage_liens": plage_liens,
            "bgp_as": bgp_as,
            "vrf": None
        },
        "routeurs": {}
    }
    print(f"AS client '{nom_as}' créé.")


def creer_vrfs() -> dict:
    """Crée les VRFs pour l'AS Provider."""
    vrfs = {}
    print("\n=== Configuration des VRFs ===")

    while True:
        nom_vrf = input("Nom de la VRF (ou 'fin' pour arrêter) : ").strip()
        if nom_vrf.lower() == "fin":
            break
        rd = input(f"  Route Distinguisher pour {nom_vrf} (ex: 100:1) : ").strip()
        rt = input(f"  Route Target pour {nom_vrf} (ex: 100:111) : ").strip()
        vrfs[nom_vrf] = {"rd": rd, "rt": rt}

    return vrfs if vrfs else None


# ============================================================
# GESTION DES ROUTEURS
# ============================================================

def ajouter_routeur(intent: dict):
    """Ajoute un routeur dans un AS existant."""
    print("\n=== Nouveau routeur ===")

    as_dispos = list(intent["AS"].keys())
    if not as_dispos:
        print("Aucun AS disponible. Créez d'abord un AS.")
        return

    nom_as = choisir_parmi(as_dispos, "Dans quel AS ajouter le routeur ?")
    nom_routeur = input("Nom du routeur (ex: PE1, P1, CE1) : ").strip()

    if nom_routeur in intent["AS"][nom_as]["routeurs"]:
        print(f"Le routeur '{nom_routeur}' existe déjà dans '{nom_as}'.")
        return

    id_routeur = int(input("ID du routeur : ").strip())

    intent["AS"][nom_as]["routeurs"][nom_routeur] = {
        "id": id_routeur,
        "interfaces": {}
    }
    print(f"Routeur '{nom_routeur}' ajouté dans '{nom_as}'.")


# ============================================================
# GESTION DES LIENS
# ============================================================

def ajouter_lien(intent: dict):
    """
    Ajoute un lien entre deux routeurs.
    Crée automatiquement l'interface des deux côtés de façon symétrique.
    La VRF n'est renseignée que côté PE (Provider), toujours null côté CE (Client).
    """
    print("\n=== Nouveau lien ===")

    # Récupération de tous les routeurs disponibles (tous AS confondus)
    tous_routeurs = []
    for nom_as, data_as in intent["AS"].items():
        for nom_routeur in data_as["routeurs"]:
            tous_routeurs.append(f"{nom_routeur} ({nom_as})")

    if len(tous_routeurs) < 2:
        print("Il faut au moins 2 routeurs pour créer un lien.")
        return

    # Sélection des deux routeurs
    choix_a = choisir_parmi(tous_routeurs, "Routeur A")
    nom_routeur_a = choix_a.split(" (")[0]
    nom_as_a = trouver_as_du_routeur(intent, nom_routeur_a)

    choix_b = choisir_parmi(tous_routeurs, "Routeur B")
    nom_routeur_b = choix_b.split(" (")[0]
    nom_as_b = trouver_as_du_routeur(intent, nom_routeur_b)

    if nom_routeur_a == nom_routeur_b:
        print("Impossible de créer un lien entre un routeur et lui-même.")
        return

    # Sélection des interfaces
    interface_a = input(f"Interface sur {nom_routeur_a} (ex: GigabitEthernet1/0) : ").strip()
    interface_b = input(f"Interface sur {nom_routeur_b} (ex: GigabitEthernet1/0) : ").strip()

    # VRF : uniquement côté Provider, null côté Client
    vrf_a = None
    vrf_b = None

    if nom_as_a == "Provider":
        vrf_a = _demander_vrf(intent, nom_routeur_a, nom_as_b)
    if nom_as_b == "Provider":
        vrf_b = _demander_vrf(intent, nom_routeur_b, nom_as_a)

    # AS BGP de chaque côté
    bgp_as_a = intent["AS"][nom_as_a]["parametres_globaux"]["bgp_as"]
    bgp_as_b = intent["AS"][nom_as_b]["parametres_globaux"]["bgp_as"]

    # Ajout côté A
    intent["AS"][nom_as_a]["routeurs"][nom_routeur_a]["interfaces"][interface_a] = {
        "voisin": nom_routeur_b,
        "vrf": vrf_a,
        "as": bgp_as_b
    }

    # Ajout côté B (symétrique)
    intent["AS"][nom_as_b]["routeurs"][nom_routeur_b]["interfaces"][interface_b] = {
        "voisin": nom_routeur_a,
        "vrf": vrf_b,
        "as": bgp_as_a
    }

    print(f"Lien créé : {nom_routeur_a}:{interface_a} <-> {nom_routeur_b}:{interface_b}")


def _demander_vrf(intent: dict, nom_routeur_pe: str, nom_as_voisin: str) -> str | None:
    """
    Demande quelle VRF associer à l'interface d'un PE vers un CE.
    Retourne None si le voisin est dans le Provider (lien interne).
    """
    if nom_as_voisin == "Provider":
        return None  # Lien interne Provider, pas de VRF

    vrfs_dispo = intent["AS"]["Provider"]["parametres_globaux"].get("vrf")
    if not vrfs_dispo:
        print("Aucune VRF disponible sur le Provider.")
        return None

    liste_vrfs = list(vrfs_dispo.keys()) + ["none"]
    choix = choisir_parmi(liste_vrfs, f"VRF pour l'interface de {nom_routeur_pe} vers ({nom_as_voisin})")
    return None if choix == "none" else choix


# ============================================================
# SAUVEGARDE / CHARGEMENT
# ============================================================

def sauvegarder(intent: dict):
    """Sauvegarde l'intent dans un fichier JSON."""
    fichier = input("Nom du fichier de sortie (défaut: intent.json) : ").strip()
    if not fichier:
        fichier = "intent.json"
    with open(fichier, "w") as f:
        json.dump(intent, f, indent=2)
    print(f"Intent sauvegardé dans '{fichier}'.")


def charger() -> dict:
    """Charge un intent depuis un fichier JSON existant."""
    fichier = input("Nom du fichier à charger : ").strip()
    try:
        with open(fichier, "r") as f:
            intent = json.load(f)
        print(f"Intent chargé depuis '{fichier}'.")
        return intent
    except FileNotFoundError:
        print(f"Fichier '{fichier}' introuvable.")
        return None
    except json.JSONDecodeError:
        print(f"Fichier '{fichier}' invalide.")
        return None


# ============================================================
# MENU PRINCIPAL
# ============================================================

def menu(intent: dict):
    actions = {
        "1": ("Ajouter l'AS Provider",   lambda: ajouter_as_provider(intent)),
        "2": ("Ajouter un AS Client",    lambda: ajouter_as_client(intent)),
        "3": ("Ajouter un routeur",      lambda: ajouter_routeur(intent)),
        "4": ("Ajouter un lien",         lambda: ajouter_lien(intent)),
        "5": ("Afficher l'intent",       lambda: print(json.dumps(intent, indent=2))),
        "6": ("Sauvegarder",             lambda: sauvegarder(intent)),
        "7": ("Quitter",                 None),
    }

    while True:
        print("\n=== Menu ===")
        for k, (label, _) in actions.items():
            print(f"  {k}. {label}")

        choix = input("Choix : ").strip()

        if choix == "7":
            print("Au revoir !")
            break
        elif choix in actions:
            _, fn = actions[choix]
            fn()
        else:
            print("Choix invalide.")


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    print("=== Générateur d'intent réseau ===")
    print("1. Créer un nouvel intent")
    print("2. Charger un intent existant")
    choix = input("Choix : ").strip()

    if choix == "2":
        intent = charger()
        if intent is None:
            print("Création d'un nouvel intent à la place.")
            intent = creer_intent()
    else:
        intent = creer_intent()

    menu(intent)
