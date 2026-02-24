# RPG Python Tkinter multijoueur

Mini projet client/serveur en Python avec :

- **Interface Tkinter** côté client.
- **Multijoueur** via sockets TCP (chat + présence des joueurs).
- **Login/Register** côté serveur.
- **Base SQLite `game.db`**.
- **Avatar stocké en BLOB** dans la base.
- **Points d'action (PA)** : max 20, recharge de 2 PA par heure.

## Fichiers

- `server.py` : serveur TCP + logique DB + authentification + PA.
- `client.py` : interface graphique Tkinter (connexion, chat, action, upload avatar).
- `game.db` : créé automatiquement au lancement du serveur.

## Lancer le projet

### 1) Démarrer le serveur

```bash
python3 server.py
```

Par défaut le serveur écoute sur `0.0.0.0:5050`.

### 2) Démarrer un ou plusieurs clients

```bash
python3 client.py
```

Ouvrir plusieurs fenêtres (ou plusieurs machines) pour tester le multijoueur.

## Gameplay simple inclus

- Bouton **Jouer (5 PA)** : consomme 5 PA.
- Si PA insuffisants, le serveur refuse l'action.
- La recharge des PA est recalculée à chaque login / requête d'état selon le temps écoulé.

## Notes sécurité (démo)

- Les mots de passe sont hashés via `PBKDF2-HMAC-SHA256` + sel aléatoire.
- Le protocole réseau est JSON sur TCP (une ligne JSON = un message).
- Pour une prod, ajouter TLS, validation stricte des entrées et gestion d'erreurs avancée.
