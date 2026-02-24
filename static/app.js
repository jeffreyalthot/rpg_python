const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const spendButton = document.getElementById('spendButton');
const statusEl = document.getElementById('status');
const playersEl = document.getElementById('players');
const paBar = document.getElementById('paBar');
const paText = document.getElementById('paText');
const menuButtons = document.getElementById('menuButtons');

let username = null;
let maxPA = 20;

const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws`);

function buttonLabel(text) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = text;
  return button;
}

function renderMenu() {
  const disconnectedMenu = ['Home', 'Login', 'Inscription'];
  const connectedMenu = [
    'Accueil',
    'Inventaire',
    'Quêtes',
    'Combats',
    'Personnage',
    'Equipe',
    'Guilde',
    'Messages',
    'Boutique',
    'Déconnection',
  ];

  const labels = username ? connectedMenu : disconnectedMenu;
  menuButtons.innerHTML = '';
  labels.forEach((label) => {
    const button = buttonLabel(label);
    if (label === 'Déconnection') {
      button.addEventListener('click', () => {
        username = null;
        renderPA(0);
        statusEl.textContent = 'Déconnecté.';
        renderMenu();
      });
    }
    menuButtons.appendChild(button);
  });
}

function renderPA(current) {
  const safe = Math.max(0, Math.min(maxPA, current));
  paBar.style.width = `${(safe / maxPA) * 100}%`;
  paText.textContent = `${safe} / ${maxPA}`;
  spendButton.disabled = !username || safe <= 0;
}

function renderPlayers(players) {
  playersEl.innerHTML = '';
  Object.entries(players).forEach(([name, state]) => {
    const li = document.createElement('li');
    li.textContent = `${name}: ${state.action_points} PA`;
    playersEl.appendChild(li);

    if (name === username) {
      renderPA(state.action_points);
    }
  });
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'snapshot') {
    renderPlayers(data.players);
  }
};

registerForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(registerForm);

  const response = await fetch('/api/register', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Erreur lors de l\'inscription';
    return;
  }

  statusEl.textContent = 'Inscription réussie. Vous pouvez vous connecter.';
  registerForm.reset();
});

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);

  const response = await fetch('/api/login', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Erreur de connexion';
    return;
  }

  username = data.username;
  maxPA = data.max_action_points;
  renderPA(data.action_points);
  statusEl.textContent = `Bienvenue ${username}. Régénération: ${data.recharge_per_hour} PA/h.`;
  spendButton.disabled = false;
  renderMenu();
});

spendButton.addEventListener('click', async () => {
  if (!username) return;

  const formData = new FormData();
  formData.append('username', username);

  const response = await fetch('/api/action', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Action impossible';
    return;
  }

  renderPA(data.action_points);
  statusEl.textContent = `Action effectuée. Il reste ${data.action_points} PA.`;
});

renderMenu();
