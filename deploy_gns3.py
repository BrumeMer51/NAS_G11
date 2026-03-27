import shutil
import os

# --- CONFIGURATION ---
# On crée une liste qui regroupe toutes les informations pour chaque routeur
liste_routeurs = [
    {
        "nom": "PE1", 
        "source": "cfg_mpls/PE1_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\d21b8fa2-f802-47f9-8719-1d6ffa2b6d0b\configs\i1_startup-config.cfg"
    },
    {
        "nom": "PE2", 
        "source": "cfg_mpls/PE2_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\126e48e8-c6ff-4a17-8ca2-50a5dd02fe6b\configs\i5_startup-config.cfg"
    },
    {
        "nom": "P1", 
        "source": "cfg_mpls/P1_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\9b3a13d8-18bb-402a-a646-75f2058e5332\configs\i2_startup-config.cfg"
    },
    {
        "nom": "P2", 
        "source": "cfg_mpls/P2_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\bc7777c9-9da9-4631-bc29-bac48a32c531\configs\i3_startup-config.cfg"
    },
    {
        "nom": "P5", 
        "source": "cfg_mpls/P5_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\933f4461-f37f-4185-8d0d-3f6fc241659a\configs\i4_startup-config.cfg"
    },
    {
        "nom": "CE1", 
        "source": "cfg_mpls/CE1_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\7d0bdea5-66bc-44c7-8084-2e1331599578\configs\i6_startup-config.cfg"
    },
    {
        "nom": "CE2", 
        "source": "cfg_mpls/CE2_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\a2296f88-a5db-450e-bac0-c84d3809731c\configs\i8_startup-config.cfg"
    },
    {
        "nom": "CE3", 
        "source": "cfg_mpls/CE3_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\132f3428-92e1-4e7e-becb-c41edb86c470\configs\i7_startup-config.cfg"
    },
    {
        "nom": "CE4", 
        "source": "cfg_mpls/CE4_startup-config.cfg", 
        "dest": r"C:\Users\mboum\GNS3\projects\NAS\TD-NAS\project-files\dynamips\5427695e-0973-4fa5-a0a5-9c02ec1bab01\configs\i9_startup-config.cfg"
    }
]

# --- TRAITEMENT ---
print(" Début du déploiement des configurations GNS3...\n")

# On boucle sur chaque routeur de la liste
for routeur in liste_routeurs:
    nom = routeur["nom"]
    src = routeur["source"]
    dst = routeur["dest"]
    
    print(f"⏳ Traitement de {nom}...")
    
    try:
        # Vérification si le fichier source existe
        if not os.path.exists(src):
            print(f"   Erreur : Le fichier source '{src}' est introuvable !")
            continue # Passe au routeur suivant sans faire planter le script
            
        # Injection (copie)
        shutil.copyfile(src, dst)
        print(f"   Config injectée avec succès pour {nom} !")

    except FileNotFoundError:
        print(f"   Erreur : Le dossier de destination GNS3 pour {nom} n'existe pas.")
    except Exception as e:
        print(f"   Une erreur inattendue pour {nom} : {e}")

print("\n Terminé ! Tu peux maintenant allumer tous tes routeurs dans GNS3.")