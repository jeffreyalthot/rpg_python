import base64
import json
import queue
import socket
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

HOST = "127.0.0.1"
PORT = 5050


class NetworkClient:
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.recv_queue = queue.Queue()
        self.running = True
        threading.Thread(target=self._receiver, daemon=True).start()

    def _receiver(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    self.running = False
                    self.recv_queue.put({"type": "disconnect"})
                    return
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.recv_queue.put(json.loads(line))
            except Exception:
                self.running = False
                self.recv_queue.put({"type": "disconnect"})
                return

    def send(self, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False) + "\n"
        self.sock.sendall(raw.encode("utf-8"))

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass


class GameApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RPG Tkinter Multijoueur")
        self.geometry("800x520")

        self.network = None
        self.username = None

        self.login_frame = tk.Frame(self)
        self.game_frame = tk.Frame(self)

        self._build_login_frame()
        self._build_game_frame()

        self.login_frame.pack(fill="both", expand=True)
        self.after(120, self._poll_messages)

    def _build_login_frame(self):
        container = tk.Frame(self.login_frame, padx=20, pady=20)
        container.pack(expand=True)

        tk.Label(container, text="Serveur:").grid(row=0, column=0, sticky="e")
        self.host_entry = tk.Entry(container, width=28)
        self.host_entry.insert(0, HOST)
        self.host_entry.grid(row=0, column=1, pady=5)

        tk.Label(container, text="Port:").grid(row=1, column=0, sticky="e")
        self.port_entry = tk.Entry(container, width=28)
        self.port_entry.insert(0, str(PORT))
        self.port_entry.grid(row=1, column=1, pady=5)

        tk.Label(container, text="Utilisateur:").grid(row=2, column=0, sticky="e")
        self.username_entry = tk.Entry(container, width=28)
        self.username_entry.grid(row=2, column=1, pady=5)

        tk.Label(container, text="Mot de passe:").grid(row=3, column=0, sticky="e")
        self.password_entry = tk.Entry(container, width=28, show="*")
        self.password_entry.grid(row=3, column=1, pady=5)

        tk.Button(container, text="Connexion", width=18, command=self.login).grid(row=4, column=0, pady=12)
        tk.Button(container, text="Inscription", width=18, command=self.register).grid(row=4, column=1, pady=12)

    def _build_game_frame(self):
        top = tk.Frame(self.game_frame)
        top.pack(fill="x", padx=10, pady=8)

        self.info_label = tk.Label(top, text="Non connecté")
        self.info_label.pack(side="left")

        tk.Button(top, text="Rafraîchir état", command=self.request_state).pack(side="right", padx=4)
        tk.Button(top, text="Jouer (5 PA)", command=self.play_action).pack(side="right", padx=4)
        tk.Button(top, text="Uploader avatar", command=self.upload_avatar).pack(side="right", padx=4)

        middle = tk.Frame(self.game_frame)
        middle.pack(fill="both", expand=True, padx=10, pady=6)

        left = tk.Frame(middle)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="Chat").pack(anchor="w")
        self.chat_box = scrolledtext.ScrolledText(left, state="disabled", height=18)
        self.chat_box.pack(fill="both", expand=True)

        bottom_chat = tk.Frame(left)
        bottom_chat.pack(fill="x", pady=4)
        self.chat_entry = tk.Entry(bottom_chat)
        self.chat_entry.pack(side="left", fill="x", expand=True)
        tk.Button(bottom_chat, text="Envoyer", command=self.send_chat).pack(side="left", padx=4)

        right = tk.Frame(middle, width=180)
        right.pack(side="left", fill="y", padx=10)
        right.pack_propagate(False)

        tk.Label(right, text="Joueurs connectés").pack(anchor="w")
        self.players_list = tk.Listbox(right)
        self.players_list.pack(fill="both", expand=True)

    def connect(self):
        if self.network:
            return True
        host = self.host_entry.get().strip()
        port_text = self.port_entry.get().strip()
        try:
            port = int(port_text)
            self.network = NetworkClient(host, port)
            return True
        except Exception as exc:
            messagebox.showerror("Connexion", f"Impossible de se connecter: {exc}")
            self.network = None
            return False

    def register(self):
        if not self.connect():
            return
        self.network.send(
            {
                "action": "register",
                "username": self.username_entry.get().strip(),
                "password": self.password_entry.get(),
            }
        )

    def login(self):
        if not self.connect():
            return
        self.network.send(
            {
                "action": "login",
                "username": self.username_entry.get().strip(),
                "password": self.password_entry.get(),
            }
        )

    def request_state(self):
        if self.network:
            self.network.send({"action": "get_state"})

    def play_action(self):
        if self.network:
            self.network.send({"action": "play_action"})

    def send_chat(self):
        text = self.chat_entry.get().strip()
        if text and self.network:
            self.network.send({"action": "chat", "message": text})
            self.chat_entry.delete(0, tk.END)

    def upload_avatar(self):
        if not self.network:
            return
        path = filedialog.askopenfilename(
            title="Choisir une image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp")],
        )
        if not path:
            return

        data = Path(path).read_bytes()
        image_b64 = base64.b64encode(data).decode("ascii")
        self.network.send({"action": "upload_avatar", "image_b64": image_b64})

    def _append_chat(self, line: str):
        self.chat_box.configure(state="normal")
        self.chat_box.insert(tk.END, line + "\n")
        self.chat_box.see(tk.END)
        self.chat_box.configure(state="disabled")

    def _set_players(self, players):
        self.players_list.delete(0, tk.END)
        for p in players:
            self.players_list.insert(tk.END, p)

    def _poll_messages(self):
        try:
            while True:
                message = self.network.recv_queue.get_nowait() if self.network else None
                if message is None:
                    break
                msg_type = message.get("type")

                if msg_type == "register":
                    kind = messagebox.showinfo if message.get("ok") else messagebox.showerror
                    kind("Inscription", message.get("message", ""))

                elif msg_type == "login":
                    if message.get("ok"):
                        self.username = message["user"]["username"]
                        self.login_frame.pack_forget()
                        self.game_frame.pack(fill="both", expand=True)
                        user = message["user"]
                        self.info_label.config(
                            text=f"{user['username']} | PA: {user['action_points']}/{user['max_action_points']}"
                        )
                        self._append_chat("Connecté au serveur.")
                        self.request_state()
                    else:
                        messagebox.showerror("Connexion", message.get("message", ""))

                elif msg_type == "state":
                    user = message.get("user", {})
                    self.info_label.config(
                        text=f"{user.get('username', '')} | PA: {user.get('action_points', 0)}/{user.get('max_action_points', 20)}"
                    )
                    if "players" in message:
                        self._set_players(message["players"])

                elif msg_type == "players":
                    self._set_players(message.get("players", []))

                elif msg_type == "play_action":
                    if message.get("ok"):
                        self._append_chat(
                            f"Action réussie. Coût: {message.get('action_cost')} PA. PA restants: {message.get('action_points')}"
                        )
                        self.request_state()
                    else:
                        messagebox.showwarning("Action", message.get("message", ""))

                elif msg_type == "chat":
                    self._append_chat(f"[{message.get('from', '???')}] {message.get('message', '')}")

                elif msg_type == "upload_avatar":
                    kind = messagebox.showinfo if message.get("ok") else messagebox.showerror
                    kind("Avatar", message.get("message", ""))

                elif msg_type == "error":
                    messagebox.showerror("Erreur", message.get("message", "Erreur inconnue"))

                elif msg_type == "disconnect":
                    messagebox.showerror("Réseau", "Connexion au serveur perdue.")
                    self.destroy()
                    return
        except queue.Empty:
            pass

        self.after(120, self._poll_messages)

    def destroy(self):
        if self.network:
            self.network.close()
        super().destroy()


if __name__ == "__main__":
    app = GameApp()
    app.mainloop()
