const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const spendButton = document.getElementById('spendButton');
const statusEl = document.getElementById('status');
const playersEl = document.getElementById('players');
const paBar = document.getElementById('paBar');
const paText = document.getElementById('paText');
const menuButtons = document.getElementById('menuButtons');
const worldMap = document.getElementById('worldMap');
const worldStats = document.getElementById('worldStats');

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

function drawPoints(ctx, world, points, color, size) {
  ctx.fillStyle = color;
  points.forEach((point) => {
    const x = Math.round((point.x / (world.width - 1)) * (ctx.canvas.width - 1));
    const y = Math.round((point.y / (world.height - 1)) * (ctx.canvas.height - 1));
    ctx.fillRect(x, y, size, size);
  });
}

function renderWorld(world) {
  if (!worldMap || !worldStats) {
    return;
  }

  const ctx = worldMap.getContext('2d');
  ctx.clearRect(0, 0, worldMap.width, worldMap.height);

  drawPoints(ctx, world, world.villages, '#22c55e', 2);
  drawPoints(ctx, world, world.starting_villages, '#0ea5e9', 3);
  drawPoints(ctx, world, world.battlefields, '#ef4444', 2);
  drawPoints(ctx, world, world.merchants, '#facc15', 2);

  worldStats.innerHTML = `
    <strong>Dimensions:</strong> ${world.width} x ${world.height} cases<br>
    <strong>Villages de départ:</strong> ${world.starting_villages.length}<br>
    <strong>Autres villages:</strong> ${world.villages.length}<br>
    <strong>Champs de bataille:</strong> ${world.battlefields.length}<br>
    <strong>Marchands ambulants:</strong> ${world.merchants.length} (déplacement: 1 case / heure)
  `;
}

async function refreshWorld() {
  if (!worldMap) {
    return;
  }

  const response = await fetch('/api/world');
  if (!response.ok) {
    worldStats.textContent = 'Impossible de charger la carte du monde.';
    return;
  }

  const world = await response.json();
  renderWorld(world);
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
refreshWorld();
setInterval(refreshWorld, 60000);
