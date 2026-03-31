import json
import os
import ipaddress

def generer_configs(fichier_json):
    with open(fichier_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    liens_inter=data["Plage_liens_inter"]


    # --- AUTOMATISATION DE L'ADRESSAGE IP ---
    # 1. Préparation des générateurs de sous-réseaux
    reseau_liens = ipaddress.IPv4Network(data["AS"]["Provider"]["parametres_globaux"]["plage_liens"])
    reseau_liens_inter = ipaddress.IPv4Network(liens_inter)
    #print(reseau_liens)  # Affiche le réseau de base pour les liens
    generateur_liens_30 = reseau_liens.subnets(new_prefix=30)
    generateur_liens_inter_30 = reseau_liens_inter.subnets(new_prefix=30)

    # Dictionnaire pour stocker le /30 attribué à chaque paire de routeurs (ex: ("P1", "PE1") : 192.168.10.0/30)
    liens_alloues = {}

    # Dictionnaire pour stocker le /30 attribué à chaque paire PE-CE de routeurs (ex: ("CE1", "PE1") : 10.0.1.0/30)
    liens_inter_alloues = {}

    def get_ip_lien(routeur_actuel, voisin):
        # Trie par ordre alphabétique pour créer une clé unique pour le lien (équivalent du routeurMin)
        cle_lien = tuple(sorted([routeur_actuel, voisin]))
        
        # Si le lien n'a pas encore de réseau, on lui attribue le prochain /30 dispo
        if cle_lien not in liens_alloues:
            liens_alloues[cle_lien] = next(generateur_liens_30)
        
        sous_reseau = liens_alloues[cle_lien]
        ip_dispos = list(sous_reseau.hosts()) # Liste des 2 IP utilisables du /30
        masque = sous_reseau.netmask
        
        # Le premier routeur par ordre alphabétique prend la 1ère IP, l'autre prend la 2ème IP
        if routeur_actuel == cle_lien[0]:
            return ip_dispos[0], masque
        else:
            return ip_dispos[1], masque
        
    def get_ip_lien_inter(routeur_actuel, voisin):
        # Trie par ordre alphabétique pour créer une clé unique pour le lien (équivalent du routeurMin)
        cle_lien = tuple(sorted([routeur_actuel, voisin]))
        
        # Si le lien n'a pas encore de réseau, on lui attribue le prochain /30 dispo
        if cle_lien not in liens_inter_alloues:
            liens_inter_alloues[cle_lien] = next(generateur_liens_inter_30)
        
        sous_reseau = liens_inter_alloues[cle_lien]
        ip_dispos = list(sous_reseau.hosts()) # Liste des 2 IP utilisables du /30
        masque = sous_reseau.netmask
        
        # Le premier routeur par ordre alphabétique prend la 1ère IP, l'autre prend la 2ème IP
        if routeur_actuel == cle_lien[0]:
            return ip_dispos[0], masque
        else:
            return ip_dispos[1], masque

    # --- GÉNÉRATION DES FICHIERS ---
    dossier_sortie = "cfg_mpls"
    os.makedirs(dossier_sortie, exist_ok=True)

    for AS_name,dataAS in data["AS"].items():
        provider=data["AS"][AS_name]
        parametres = provider["parametres_globaux"]
        routeurs_provider = provider["routeurs"]
        ospf_proc = parametres["ospf_process"]
        bgp_as = parametres["bgp_as"]

        

        for nom_routeur, infos in routeurs_provider.items():
            nom_fichier = f"{dossier_sortie}/{nom_routeur}_startup-config.cfg"
            
            # Calcul de la Loopback (ex: id=1 -> 192.168.255.1)
            base_loopback = parametres["plage_loopbacks"].replace("0/24", str(infos["id"]))
            ip_loopback = ipaddress.IPv4Address(base_loopback)
            router_id_ospf = f"{infos['id']}.{infos['id']}.{infos['id']}.{infos['id']}"

            with open(nom_fichier, "w", encoding="utf-8") as cfg:
                # En-tête
                cfg.write("!\n")
                cfg.write("version 15.2\n")
                cfg.write("service timestamps debug datetime msec\n")
                cfg.write("service timestamps log datetime msec\n")
                cfg.write("!\n")
                cfg.write(f"hostname {nom_routeur}\n")
                cfg.write("!\n")
                cfg.write("boot-start-marker\n")
                cfg.write("boot-end-marker\n")

                # Configuration VRF (si applicable et seulement pour les PE) :
                if (parametres["vrf"] != None) and ("PE" in nom_routeur) :
                    for client in parametres["vrf"] :
                        cfg.write(f"vrf definition {client} \n")
                        cfg.write(f" rd {parametres["vrf"][client]["rd"]} \n")
                        cfg.write(f" route-target export {parametres["vrf"][client]["rt"]} \n")
                        cfg.write(f" route-target import {parametres["vrf"][client]["rt"]} \n")
                        cfg.write(" !\n")
                        cfg.write(" address-family ipv4 \n")
                        cfg.write(" exit-address-family \n")
                        cfg.write("!\n")

                cfg.write("!\n!\n!\n")
                cfg.write("no aaa new-model\n")
                cfg.write("no ip icmp rate-limit unreachable\n")
                cfg.write("ip cef\n")
                cfg.write("!\n!\n!\n!\n!\n!\n")
                cfg.write("no ip domain lookup\n")
                cfg.write("no ipv6 cef\n")
                cfg.write("!\n!\n")
                cfg.write("mpls label protocol ldp\n")
                cfg.write("multilink bundle-name authenticated\n")
                cfg.write("!\n!\n!\n!\n!\n!\n!\n!\n!\n")
                cfg.write("ip tcp synwait-time 5\n")
                cfg.write("!\n!\n!\n!\n!\n!\n!\n!\n!\n!\n!\n!\n")

                # Configuration Loopback
                cfg.write("interface Loopback0\n")
                cfg.write(f" ip address {ip_loopback} 255.255.255.255\n")
                cfg.write("!\n")

                # Interface FastEthernet0/0 (Désactivée par défaut)
                cfg.write("interface FastEthernet0/0\n")
                cfg.write(" no ip address\n")
                cfg.write(" shutdown\n")
                cfg.write(" duplex full\n")
                cfg.write("!\n")

                # Interfaces GigabitEthernet connectées
                for nom_iface, iface_data in infos["interfaces"].items():
                    voisin = iface_data.get("voisin")
                    cfg.write(f"interface {nom_iface}\n")

                    if "P" in nom_routeur and voisin :
                        if iface_data.get("vrf") != None :
                            cfg.write(f" vrf forwarding {iface_data.get('vrf')}\n")
                        if "CE" not in voisin :
                            ip_iface, masque = get_ip_lien(nom_routeur, voisin)
                            cfg.write(f" ip address {ip_iface} {masque}\n")
                            cfg.write(" negotiation auto\n")
                            cfg.write(" mpls ip\n")
                        else :
                            ip_iface, masque = get_ip_lien_inter(nom_routeur, voisin)
                            cfg.write(f" ip address {ip_iface} {masque}\n")
                            cfg.write(" negotiation auto\n")

                    elif "C" in nom_routeur and voisin :
                        ip_iface, masque = get_ip_lien_inter(nom_routeur, voisin)
                        cfg.write(f" ip address {ip_iface} {masque}\n")
                        cfg.write(" negotiation auto\n")

                    else:
                        cfg.write(" no ip address\n")
                        cfg.write(" shutdown\n")
                        cfg.write(" negotiation auto\n")
                    cfg.write("!\n")

                # Routage OSPF
                if ospf_proc != None:
                    cfg.write(f"router ospf {ospf_proc}\n")
                    cfg.write(f" router-id {router_id_ospf}\n")
                    # Network pour la loopback : 
                    cfg.write(f" network {ip_loopback} 0.0.0.0 area 0\n")
                    # Pour chaque interface connectée, on ajoute une ligne "network" dans OSPF :
                    for nom_iface, iface_data in infos["interfaces"].items():
                        voisin = iface_data.get("voisin")
                        if voisin :
                            if "P" in nom_routeur and "CE" not in voisin :
                                ip_iface, masque = get_ip_lien(nom_routeur, voisin)
                                wildcard = ipaddress.IPv4Address(int(masque) ^ 0xFFFFFFFF)  # Calcul du wildcard à partir du masque
                                print(wildcard)
                                cfg.write(f" network {ip_iface} {wildcard} area 0\n")
                    cfg.write("!\n")

                # Config BGP pour les PE et CE : 
                if ("PE" in nom_routeur) or ("CE" in nom_routeur) :
                    cfg.write("!\n")
                    cfg.write(f"router bgp {bgp_as}\n")
                    cfg.write(" bgp log-neighbor-changes\n")

                    # On ajoute les voisins iBGP pour les PE :
                    if ("PE" in nom_routeur) :
                        for autre_nom, autre_infos in routeurs_provider.items():
                            if "PE" in autre_nom and autre_nom != nom_routeur:
                                autre_ip_loop = parametres["plage_loopbacks"].replace("0/24", str(autre_infos["id"]))
                                cfg.write(f" neighbor {autre_ip_loop} remote-as 100\n")
                                cfg.write(f" neighbor {autre_ip_loop} update-source Loopback0\n")
                                cfg.write(f"!\n")
                        cfg.write(f" address-family vpnv4\n")

                        # On ajoute les voisins iBGP dans l'address-family vpnv4 : 
                        for autre_nom, autre_infos in routeurs_provider.items():
                            if "PE" in autre_nom and autre_nom != nom_routeur:
                                # RECALCUL de l'IP ici pour ne pas utiliser la mauvaise variable
                                ip_v_ibgp = parametres["plage_loopbacks"].replace("0/24", str(autre_infos["id"]))
                                cfg.write(f"  neighbor {ip_v_ibgp} activate\n")
                                cfg.write(f"  neighbor {ip_v_ibgp} send-community both\n")
                        cfg.write(f" exit-address-family\n !\n")


                    # Ajout des clients en eBGP avec leur VRF : 
                    for nom_iface,infos_iface in routeurs_provider[nom_routeur]["interfaces"].items():
                        autre_nom = infos_iface.get("voisin")
                        vrf = infos_iface.get("vrf")
                        as_voisin = infos_iface.get("as")

                        if "CE" in autre_nom and vrf != None:
                            autre_ip_loop = get_ip_lien_inter(autre_nom, nom_routeur)[0]
                            cfg.write(f" address-family ipv4 vrf {vrf}\n")
                            cfg.write(f"  neighbor {autre_ip_loop} remote-as {as_voisin}\n")
                            cfg.write(f"  neighbor {autre_ip_loop} activate\n")
                            cfg.write(f" exit-address-family\n !\n")
                        
                        if "PE" in autre_nom and "CE" in nom_routeur : 
                            autre_ip_loop = get_ip_lien_inter(autre_nom, nom_routeur)[0]
                            cfg.write(f" neighbor {autre_ip_loop} remote-as {as_voisin}\n")
                            cfg.write(f" neighbor {autre_ip_loop} activate\n")
                            
                    
                    
                
                cfg.write("!\n")
                cfg.write("ip forward-protocol nd\n")
                cfg.write("!\n!\n")
                cfg.write("no ip http server\n")
                cfg.write("no ip http secure-server\n")
                cfg.write("!\n!\n")
                
                cfg.write("!\n!\n")
                cfg.write("control-plane\n")
                cfg.write("!\n!\n")

                # Lignes de fin
                cfg.write("line con 0\n")
                cfg.write(" exec-timeout 0 0\n")
                cfg.write(" privilege level 15\n")
                cfg.write(" logging synchronous\n")
                cfg.write(" stopbits 1\n")
                cfg.write("line aux 0\n")
                cfg.write(" exec-timeout 0 0\n")
                cfg.write(" privilege level 15\n")
                cfg.write(" logging synchronous\n")
                cfg.write(" stopbits 1\n")
                cfg.write("line vty 0 4\n")
                cfg.write(" login\n")
                cfg.write("!\n!\nend\n")

            print(f"Fichier généré avec succès : {nom_fichier}")

if __name__ == "__main__":
    generer_configs("intention_manuel.json")
