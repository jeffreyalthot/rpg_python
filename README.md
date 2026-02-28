# RPG Python - Site multijoueur à Points d'Action

Ce projet propose un mini site web multijoueur pour un jeu basé sur les **Points d'Action (PA)**.

## Règles implémentées
- Chaque joueur possède un maximum de **20 PA**.
- La régénération est de **2 PA par heure**.
- Un bouton "Utiliser 1 PA" permet de dépenser des points.
- Tous les clients connectés voient les mises à jour en temps réel.
- La barre de PA est affichée **en haut à gauche**, juste sous les boutons de navigation dans l'en-tête.
- Une action **Explorer la zone** consomme 1 PA et applique des récompenses selon le type de case (XP, or, PV, objets).
- Les statistiques du héros (niveau, inventaire) sont maintenant pilotées par le serveur à la connexion et pendant l'exploration.
- Nouveau système de **guilde**: création/rejoindre/quitter, classement des guildes en direct et chat interne pour coordonner les joueurs.
- Ajout d'un **canal de chat mondial** pour discuter avec toute la communauté connectée en temps réel.
- Nouvelle **bourse de groupes (LFG)**: publication d'annonces rapides (activité + message) pour recruter des joueurs en direct.
- Nouveau système **Alliés & invitations**: envoi/acceptation d'invitations, suivi des amis en ligne et retrait d'alliés depuis le hub de jeu.
- Ajout d'un système **"Je rejoins"** sur chaque annonce LFG avec compteur d'intéressés synchronisé en temps réel.
- Ajout d'un **ready check LFG**: les membres d'un groupe peuvent se marquer prêts, et le leader peut lancer l'escouade uniquement lorsque tout le monde est prêt.
- Nouveau **fil des chroniques communautaires** en temps réel: met en avant les victoires en duel, exploits de raid, saisons de contrat et mouvements de guildes pour dynamiser la rétention.
- Nouveau **classement JcJ saisonnier** avec suivi des victoires/défaites et top 10 diffusé en temps réel.
- Nouveau **tableau de contrats communautaires**: tous les joueurs peuvent contribuer en PA pour débloquer des récompenses de saison et un classement de contributeurs en direct.
- Extension du catalogue avec de nouveaux objets (images SVG + stats) pour enrichir les builds multijoueur.
- Nouveau **défi quotidien communautaire**: progression en exploration/social/combat, récompense de fidélité et classement des joueurs les plus réguliers.
- Modération du chat intégrée: filtre de mots toxiques + anti-spam (cooldown 3s et blocage des doublons) pour sécuriser les canaux communautaires.
- Nouveau système de **recommandations sociales**: chaque joueur peut valoriser jusqu'à 3 coéquipiers par jour, avec classement communautaire anti-abus pour encourager le fair-play.
- Nouveau **Conseil communautaire**: sondage en direct en jeu avec vote unique par saison, récompense légère pour la participation et rotation automatique du thème après quorum.

## Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer le serveur
```bash
uvicorn app:app --reload
```

Puis ouvrez: `http://127.0.0.1:8000`

## Tests
```bash
pytest -q
```


## Authentification
- Inscription avec: username unique, mot de passe hashé, email, prénom, nom, date de naissance.
- Connexion via username + mot de passe.
- Le menu de l'en-tête change selon l'état connecté/déconnecté.
- Une **carte du monde 5000 x 5000** est exposée via `/api/world` et affichée côté client.
- Génération de contenu monde: **10 villages de départ**, **50 autres villages**, **35 champs de bataille**.
- **25 marchands ambulants** se déplacent automatiquement d'**1 case par heure**.
