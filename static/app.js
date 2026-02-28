const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const spendButton = document.getElementById('spendButton');
const exploreButton = document.getElementById('exploreButton');
const quickBattleButton = document.getElementById('quickBattle');
const statusEl = document.getElementById('status');
const playersEl = document.getElementById('players');
const paBar = document.getElementById('paBar');
const paText = document.getElementById('paText');
const menuButtons = document.getElementById('menuButtons');
const worldMap = document.getElementById('worldMap');
const localMap = document.getElementById('localMap');
const worldStats = document.getElementById('worldStats');
const heroStats = document.getElementById('heroStats');
const inventoryEl = document.getElementById('inventory');
const questsEl = document.getElementById('quests');
const activityLogEl = document.getElementById('activityLog');
const tileImageEl = document.getElementById('tileImage');
const tileTitleEl = document.getElementById('tileTitle');
const tileDescriptionEl = document.getElementById('tileDescription');
const tileActionsEl = document.getElementById('tileActions');
const guildStatusEl = document.getElementById('guildStatus');
const guildNameInput = document.getElementById('guildName');
const createGuildButton = document.getElementById('createGuildButton');
const joinGuildButton = document.getElementById('joinGuildButton');
const leaveGuildButton = document.getElementById('leaveGuildButton');
const guildRankingEl = document.getElementById('guildRanking');
const guildChatEl = document.getElementById('guildChat');
const guildMessageInput = document.getElementById('guildMessage');
const sendGuildMessageButton = document.getElementById('sendGuildMessageButton');

let username = null;
let maxPA = 20;
let worldState = null;
let worldPositions = new Map();
let currentGuild = null;
let guildChatMessages = [];

const hero = {
  level: 1,
  xp: 0,
  gold: 90,
  hp: 100,
  maxHp: 100,
  location: 'Village d\'Aube',
  x: 0,
  y: 0,
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

function keyOf(x, y) {
  return `${x},${y}`;
}

function buildPositionIndex(world) {
  const index = new Map();
  world.starting_villages.forEach((village) => {
    index.set(keyOf(village.x, village.y), { kind: 'starting_village', name: village.name });
  });
  world.villages.forEach((village) => {
    index.set(keyOf(village.x, village.y), { kind: 'village', name: village.name });
  });
  world.battlefields.forEach((battlefield) => {
    index.set(keyOf(battlefield.x, battlefield.y), { kind: 'battlefield', name: battlefield.name });
  });
  world.merchants.forEach((merchant) => {
    index.set(keyOf(merchant.x, merchant.y), { kind: 'merchant', name: merchant.name });
  });
  return index;
}

function getTileInfo(x, y) {
  const fixed = worldPositions.get(keyOf(x, y));
  if (fixed) {
    return fixed;
  }
  return { kind: 'plain', name: 'Plaine sauvage' };
}

function tileImageData(tile, x, y) {
  const base = {
    plain: ['#0f172a', '#1d4ed8', '#334155'],
    village: ['#052e16', '#22c55e', '#14532d'],
    starting_village: ['#082f49', '#0ea5e9', '#155e75'],
    battlefield: ['#450a0a', '#ef4444', '#7f1d1d'],
    merchant: ['#422006', '#facc15', '#92400e'],
  }[tile.kind] || ['#0f172a', '#1d4ed8', '#334155'];

  const label = `${tile.name} • ${x},${y}`;
  const svg = `
  <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 420'>
    <defs>
      <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
        <stop offset='0%' stop-color='${base[0]}' />
        <stop offset='55%' stop-color='${base[1]}' />
        <stop offset='100%' stop-color='${base[2]}' />
      </linearGradient>
    </defs>
    <rect width='1200' height='420' fill='url(#g)' />
    <circle cx='230' cy='190' r='115' fill='rgba(255,255,255,0.08)' />
    <circle cx='980' cy='200' r='145' fill='rgba(255,255,255,0.08)' />
    <text x='70' y='300' fill='white' font-family='Verdana, sans-serif' font-size='58' font-weight='700'>${label}</text>
  </svg>`;

  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function canMoveTo(x, y) {
  if (!worldState) {
    return false;
  }
  return x >= 0 && y >= 0 && x < worldState.width && y < worldState.height;
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
        exploreButton.disabled = true;
        quickBattleButton.disabled = true;
        statusEl.textContent = 'Déconnecté.';
        currentGuild = null;
        guildChatMessages = [];
        renderGuildStatus();
        renderGuildChat();
        renderMenu();
        renderActionPanel();
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
  exploreButton.disabled = !username || safe <= 0;
  quickBattleButton.disabled = !username || safe <= 0;
}

function syncHero(serverHero) {
  if (!serverHero) {
    return;
  }

  hero.level = serverHero.level;
  hero.xp = serverHero.xp;
  hero.gold = serverHero.gold;
  hero.hp = serverHero.hp;
  hero.maxHp = serverHero.max_hp;
  hero.inventory = [...serverHero.inventory];
}

function renderHeroStats() {
  heroStats.innerHTML = `
    <li><strong>Niveau:</strong> ${hero.level}</li>
    <li><strong>XP:</strong> ${hero.xp} / 100</li>
    <li><strong>PV:</strong> ${hero.hp} / ${hero.maxHp}</li>
    <li><strong>Or:</strong> ${hero.gold}</li>
    <li><strong>Position:</strong> (${hero.x}, ${hero.y}) - ${hero.location}</li>
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


function renderGuildRanking(guilds = []) {
  if (!guildRankingEl) {
    return;
  }

  guildRankingEl.innerHTML = '';
  if (!guilds.length) {
    const li = document.createElement('li');
    li.textContent = 'Aucune guilde active pour le moment.';
    guildRankingEl.appendChild(li);
    return;
  }

  guilds.slice(0, 8).forEach((guild, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${guild.name} — ${guild.member_count} membre(s)`;
    guildRankingEl.appendChild(li);
  });
}

function renderGuildChat() {
  if (!guildChatEl) {
    return;
  }

  guildChatEl.innerHTML = '';
  if (!guildChatMessages.length) {
    const li = document.createElement('li');
    li.textContent = currentGuild ? 'Aucun message pour le moment.' : 'Rejoignez une guilde pour débloquer le chat.';
    guildChatEl.appendChild(li);
    return;
  }

  [...guildChatMessages].reverse().forEach((entry) => {
    const li = document.createElement('li');
    const time = new Date(entry.created_at).toLocaleTimeString();
    li.textContent = `[${time}] ${entry.author}: ${entry.message}`;
    guildChatEl.appendChild(li);
  });
}

function renderGuildStatus() {
  if (!guildStatusEl) {
    return;
  }

  if (!username) {
    guildStatusEl.textContent = 'Connectez-vous pour rejoindre une guilde.';
    return;
  }

  guildStatusEl.textContent = currentGuild
    ? `Guilde active: ${currentGuild}. Coordination en temps réel disponible.`
    : 'Aucune guilde: créez-en une ou rejoignez vos alliés.';
}

async function refreshGuilds() {
  const response = await fetch('/api/guilds');
  if (!response.ok) {
    return;
  }
  const data = await response.json();
  renderGuildRanking(data.guilds || []);
}

async function createOrJoinGuild(mode) {
  if (!username || !guildNameInput) {
    return;
  }

  const guildName = guildNameInput.value.trim();
  if (guildName.length < 3) {
    statusEl.textContent = 'Le nom de guilde doit contenir au moins 3 caractères.';
    return;
  }

  const formData = new FormData();
  formData.append('username', username);
  formData.append('guild_name', guildName);

  const endpoint = mode === 'create' ? '/api/guilds/create' : '/api/guilds/join';
  const response = await fetch(endpoint, { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || 'Action de guilde impossible.';
    return;
  }

  currentGuild = data.guild;
  guildChatMessages = data.chat || [];
  renderGuildStatus();
  renderGuildChat();
  refreshGuilds();
  statusEl.textContent = `Vous êtes maintenant dans la guilde ${currentGuild}.`;
  addLog(`Guilde: ${mode === 'create' ? 'création' : 'adhésion'} ${currentGuild}.`);
}

async function leaveGuild() {
  if (!username) {
    return;
  }

  const formData = new FormData();
  formData.append('username', username);

  const response = await fetch('/api/guilds/leave', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || 'Impossible de quitter la guilde.';
    return;
  }

  currentGuild = null;
  guildChatMessages = [];
  renderGuildStatus();
  renderGuildChat();
  refreshGuilds();
  statusEl.textContent = 'Vous avez quitté la guilde.';
  addLog('Sortie de guilde confirmée.');
}

async function sendGuildMessage() {
  if (!username || !guildMessageInput) {
    return;
  }

  const content = guildMessageInput.value.trim();
  if (content.length < 2) {
    statusEl.textContent = 'Le message doit contenir au moins 2 caractères.';
    return;
  }

  const formData = new FormData();
  formData.append('username', username);
  formData.append('message', content);

  const response = await fetch('/api/guilds/chat', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || 'Message non envoyé.';
    return;
  }

  currentGuild = data.guild;
  guildChatMessages = data.chat || [];
  guildMessageInput.value = '';
  renderGuildStatus();
  renderGuildChat();
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

function renderLocalMap() {
  if (!localMap || !worldState) {
    return;
  }

  const ctx = localMap.getContext('2d');
  const size = 20;
  const radius = 10;
  const originX = hero.x - radius;
  const originY = hero.y - radius;

  ctx.clearRect(0, 0, localMap.width, localMap.height);

  for (let row = 0; row < 21; row += 1) {
    for (let col = 0; col < 21; col += 1) {
      const worldX = originX + col;
      const worldY = originY + row;
      const tile = canMoveTo(worldX, worldY) ? getTileInfo(worldX, worldY) : { kind: 'void' };
      const color = {
        plain: '#0f172a',
        village: '#14532d',
        starting_village: '#155e75',
        battlefield: '#7f1d1d',
        merchant: '#78350f',
        void: '#020617',
      }[tile.kind] || '#0f172a';

      ctx.fillStyle = color;
      ctx.fillRect(col * size, row * size, size, size);
      ctx.strokeStyle = '#1e293b';
      ctx.strokeRect(col * size, row * size, size, size);
    }
  }

  ctx.fillStyle = '#a855f7';
  ctx.fillRect(radius * size + 4, radius * size + 4, size - 8, size - 8);
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

  const heroPixelX = Math.round((hero.x / (world.width - 1)) * (ctx.canvas.width - 1));
  const heroPixelY = Math.round((hero.y / (world.height - 1)) * (ctx.canvas.height - 1));
  ctx.fillStyle = '#a855f7';
  ctx.fillRect(heroPixelX - 2, heroPixelY - 2, 5, 5);

  worldStats.innerHTML = `
    <strong>Dimensions:</strong> ${world.width} x ${world.height} cases<br>
    <strong>Villages de départ:</strong> ${world.starting_villages.length}<br>
    <strong>Autres villages:</strong> ${world.villages.length}<br>
    <strong>Champs de bataille:</strong> ${world.battlefields.length}<br>
    <strong>Marchands ambulants:</strong> ${world.merchants.length} (déplacement: 1 case / heure)
  `;

  renderLocalMap();
}

function renderActionPanel() {
  if (!tileActionsEl || !tileTitleEl || !tileDescriptionEl || !tileImageEl) {
    return;
  }

  tileActionsEl.innerHTML = '';

  if (!username || !worldState) {
    tileTitleEl.textContent = 'Zone inconnue';
    tileDescriptionEl.textContent = 'Connectez-vous pour afficher les actions de la case.';
    tileImageEl.src = tileImageData({ kind: 'plain', name: 'Brouillard de guerre' }, hero.x, hero.y);
    return;
  }

  const tile = getTileInfo(hero.x, hero.y);
  hero.location = tile.name;

  tileTitleEl.textContent = `${tile.name} (${hero.x}, ${hero.y})`;
  tileDescriptionEl.textContent = {
    plain: 'Plaine ouverte: vous pouvez voyager, fouiller et monter un camp rapide.',
    village: 'Village: commerces, repos et quêtes locales disponibles.',
    starting_village: 'Village de départ: zone sûre pour recruter et se préparer.',
    battlefield: 'Champ de bataille: danger élevé, récompenses importantes.',
    merchant: 'Marchand ambulant: vente d\'objets rares et ravitaillement.',
  }[tile.kind] || 'Zone neutre.';
  tileImageEl.src = tileImageData(tile, hero.x, hero.y);

  const movement = [
    { label: 'Aller au Nord', x: hero.x, y: hero.y - 1 },
    { label: 'Aller au Sud', x: hero.x, y: hero.y + 1 },
    { label: 'Aller à l\'Ouest', x: hero.x - 1, y: hero.y },
    { label: 'Aller à l\'Est', x: hero.x + 1, y: hero.y },
  ].filter((next) => canMoveTo(next.x, next.y));

  movement.forEach((next) => {
    const button = buttonLabel(`${next.label} (1 PA)`);
    button.addEventListener('click', async () => {
      const ok = await spendAction();
      if (!ok) {
        return;
      }
      hero.x = next.x;
      hero.y = next.y;
      renderHeroStats();
      renderWorld(worldState);
      renderActionPanel();
      addLog(`Déplacement vers (${hero.x}, ${hero.y}).`);
    });
    tileActionsEl.appendChild(button);
  });

  const contextActions = {
    plain: ['Fouiller la zone', 'Installer un camp'],
    village: ['Entrer dans la taverne', 'Accepter une quête', 'Soigner le héros'],
    starting_village: ['Parler au mentor', 'Acheter un équipement de base'],
    battlefield: ['Lancer un combat tactique', 'Reconnaître les lignes ennemies'],
    merchant: ['Marchander des objets', 'Vendre le butin'],
  }[tile.kind] || ['Observer les environs'];

  contextActions.forEach((label) => {
    const button = buttonLabel(label);
    button.addEventListener('click', () => {
      statusEl.textContent = `${label} effectué à ${tile.name}.`;
      addLog(`${label} - ${tile.name}.`);
    });
    tileActionsEl.appendChild(button);
  });
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
  worldPositions = buildPositionIndex(worldState);

  if (!hero.location && worldState.starting_villages.length) {
    hero.location = worldState.starting_villages[0].name;
  }

  renderWorld(worldState);
  renderActionPanel();
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

async function exploreCurrentTile() {
  if (!username) {
    return;
  }

  const tile = getTileInfo(hero.x, hero.y);
  const formData = new FormData();
  formData.append('username', username);
  formData.append('tile_kind', tile.kind);

  const response = await fetch('/api/adventure', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Exploration impossible';
    return;
  }

  renderPA(data.action_points);
  syncHero(data.hero);
  renderHeroStats();
  renderInventory();

  const hpText = data.outcome.hp_delta >= 0 ? `+${data.outcome.hp_delta}` : `${data.outcome.hp_delta}`;
  let summary = `${data.outcome.summary}: +${data.outcome.xp_gain} XP, +${data.outcome.gold_gain} or, PV ${hpText}.`;
  if (data.outcome.item_found) {
    summary += ` Objet trouvé: ${data.outcome.item_found}.`;
  }
  if (data.outcome.level_ups > 0) {
    summary += ` Niveau supérieur x${data.outcome.level_ups} !`;
  }

  statusEl.textContent = summary;
  addLog(summary);
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
    hero.x = zone.x;
    hero.y = zone.y;
    hero.location = zone.name;
  }

  renderHeroStats();
  renderInventory();
  renderWorld(worldState);
  renderActionPanel();

  const summary = win ? `Victoire ! +${xpGain} XP, +${goldGain} or.` : `Défaite courageuse. +${xpGain} XP, +${goldGain} or.`;
  statusEl.textContent = `${summary} ${hero.hp}/${hero.maxHp} PV.`;
  addLog(summary);
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'snapshot') {
    renderPlayers(data.players);
    renderGuildRanking(data.guilds || []);
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
  syncHero(data.hero);
  currentGuild = data.guild || null;
  guildChatMessages = data.guild_chat || [];

  if (worldState?.starting_villages?.length) {
    const start = worldState.starting_villages[0];
    hero.x = start.x;
    hero.y = start.y;
    hero.location = start.name;
  }

  renderPA(data.action_points);
  statusEl.textContent = `Bienvenue ${username}. Régénération: ${data.recharge_per_hour} PA/h.`;
  spendButton.disabled = false;
  exploreButton.disabled = false;
  quickBattleButton.disabled = false;
  renderMenu();
  renderHeroStats();
  renderWorld(worldState);
  renderActionPanel();
  renderGuildStatus();
  renderGuildChat();
  refreshGuilds();
  addLog(`Bienvenue ${username}, ton aventure commence.`);
});

spendButton.addEventListener('click', async () => {
  const ok = await spendAction();
  if (ok) {
    addLog('Vous avez utilisé 1 PA pour une action stratégique.');
  }
});

exploreButton.addEventListener('click', async () => {
  await exploreCurrentTile();
});

quickBattleButton.addEventListener('click', async () => {
  const ok = await spendAction();
  if (ok) {
    runQuickBattle();
  }
});


createGuildButton?.addEventListener('click', async () => {
  await createOrJoinGuild('create');
});

joinGuildButton?.addEventListener('click', async () => {
  await createOrJoinGuild('join');
});

leaveGuildButton?.addEventListener('click', async () => {
  await leaveGuild();
});

sendGuildMessageButton?.addEventListener('click', async () => {
  await sendGuildMessage();
});

renderMenu();
renderHeroStats();
renderInventory();
renderQuests();
renderActionPanel();
renderGuildStatus();
renderGuildChat();
addLog('Le portail d\'Aetheria est ouvert.');
refreshWorld();
refreshGuilds();
setInterval(refreshWorld, 60000);
