const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const spendButton = document.getElementById('spendButton');
const quickBattleButton = document.getElementById('quickBattle');
const statusEl = document.getElementById('status');
const playersEl = document.getElementById('players');
const paBar = document.getElementById('paBar');
const paText = document.getElementById('paText');
const menuButtons = document.getElementById('menuButtons');
const worldMap = document.getElementById('worldMap');
const worldStats = document.getElementById('worldStats');
const heroStats = document.getElementById('heroStats');
const inventoryEl = document.getElementById('inventory');
const questsEl = document.getElementById('quests');
const activityLogEl = document.getElementById('activityLog');

let username = null;
let maxPA = 20;
let worldState = null;

const hero = {
  level: 1,
  xp: 0,
  gold: 90,
  hp: 100,
  maxHp: 100,
  location: 'Village d\'Aube',
  inventory: ['Épée rouillée', 'Potion de soin', 'Cape de voyage'],
  quests: [
    'Explorer 3 villages voisins',
    'Vaincre 2 ennemis en zone de combat',
    'Trouver un marchand rare',
  ],
};

const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws`);

function buttonLabel(text) {
  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = text;
  return button;
}

function addLog(message) {
  if (!activityLogEl) {
    return;
  }

  const li = document.createElement('li');
  li.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  activityLogEl.prepend(li);

  while (activityLogEl.children.length > 8) {
    activityLogEl.removeChild(activityLogEl.lastChild);
  }
}

function renderMenu() {
  const disconnectedMenu = ['Accueil', 'Login', 'Inscription'];
  const connectedMenu = ['Accueil', 'Inventaire', 'Quêtes', 'Combats', 'Personnage', 'Équipe', 'Guilde', 'Messages', 'Boutique', 'Déconnexion'];

  const labels = username ? connectedMenu : disconnectedMenu;
  menuButtons.innerHTML = '';
  labels.forEach((label) => {
    const button = buttonLabel(label);
    if (label === 'Déconnexion') {
      button.addEventListener('click', () => {
        username = null;
        renderPA(0);
        spendButton.disabled = true;
        quickBattleButton.disabled = true;
        statusEl.textContent = 'Déconnecté.';
        renderMenu();
        addLog('Vous avez quitté le monde.');
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
  quickBattleButton.disabled = !username || safe <= 0;
}

function renderHeroStats() {
  heroStats.innerHTML = `
    <li><strong>Niveau:</strong> ${hero.level}</li>
    <li><strong>XP:</strong> ${hero.xp} / 100</li>
    <li><strong>PV:</strong> ${hero.hp} / ${hero.maxHp}</li>
    <li><strong>Or:</strong> ${hero.gold}</li>
    <li><strong>Position:</strong> ${hero.location}</li>
  `;
}

function renderInventory() {
  inventoryEl.innerHTML = '';
  hero.inventory.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    inventoryEl.appendChild(li);
  });
}

function renderQuests() {
  questsEl.innerHTML = '';
  hero.quests.forEach((quest) => {
    const li = document.createElement('li');
    li.textContent = quest;
    questsEl.appendChild(li);
  });
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

  worldState = await response.json();
  renderWorld(worldState);
}

async function spendAction() {
  if (!username) {
    return false;
  }

  const formData = new FormData();
  formData.append('username', username);

  const response = await fetch('/api/action', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Action impossible';
    return false;
  }

  renderPA(data.action_points);
  statusEl.textContent = `Action effectuée. Il reste ${data.action_points} PA.`;
  return true;
}

function runQuickBattle() {
  const win = Math.random() > 0.45;
  const xpGain = win ? 30 : 12;
  const goldGain = win ? 25 : 6;
  const hpLoss = win ? 8 : 18;

  hero.xp += xpGain;
  hero.gold += goldGain;
  hero.hp = Math.max(0, hero.hp - hpLoss);

  if (hero.xp >= 100) {
    hero.level += 1;
    hero.xp -= 100;
    hero.maxHp += 15;
    hero.hp = hero.maxHp;
    hero.inventory.push('Rune ancienne');
    addLog('Niveau supérieur atteint ! Une Rune ancienne a été ajoutée à l\'inventaire.');
  }

  if (worldState?.battlefields?.length) {
    const zone = worldState.battlefields[Math.floor(Math.random() * worldState.battlefields.length)];
    hero.location = `Front (${zone.x}, ${zone.y})`;
  }

  renderHeroStats();
  renderInventory();

  const summary = win ? `Victoire ! +${xpGain} XP, +${goldGain} or.` : `Défaite courageuse. +${xpGain} XP, +${goldGain} or.`;
  statusEl.textContent = `${summary} ${hero.hp}/${hero.maxHp} PV.`;
  addLog(summary);
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
  addLog('Compte créé avec succès.');
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
  quickBattleButton.disabled = false;
  renderMenu();
  addLog(`Bienvenue ${username}, ton aventure commence.`);
});

spendButton.addEventListener('click', async () => {
  const ok = await spendAction();
  if (ok) {
    addLog('Vous avez utilisé 1 PA pour une action stratégique.');
  }
});

quickBattleButton.addEventListener('click', async () => {
  const ok = await spendAction();
  if (ok) {
    runQuickBattle();
  }
});

renderMenu();
renderHeroStats();
renderInventory();
renderQuests();
addLog('Le portail d\'Aetheria est ouvert.');
refreshWorld();
setInterval(refreshWorld, 60000);
