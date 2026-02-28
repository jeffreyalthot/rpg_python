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
- Nouveau **classement JcJ saisonnier** avec suivi des victoires/défaites et top 10 diffusé en temps réel.
- Extension du catalogue avec de nouveaux objets (images SVG + stats) pour enrichir les builds multijoueur.

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
