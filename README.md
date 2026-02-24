# RPG Python - Site multijoueur à Points d'Action

Ce projet propose un mini site web multijoueur pour un jeu basé sur les **Points d'Action (PA)**.

## Règles implémentées
- Chaque joueur possède un maximum de **20 PA**.
- La régénération est de **2 PA par heure**.
- Un bouton "Utiliser 1 PA" permet de dépenser des points.
- Tous les clients connectés voient les mises à jour en temps réel.
- La barre de PA est affichée **en haut à gauche**, juste sous les boutons de navigation dans l'en-tête.

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
