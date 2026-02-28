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
const globalChatEl = document.getElementById('globalChat');
const globalMessageInput = document.getElementById('globalMessage');
const sendGlobalMessageButton = document.getElementById('sendGlobalMessageButton');
const partyActivityInput = document.getElementById('partyActivity');
const partyMessageInput = document.getElementById('partyMessage');
const postPartyButton = document.getElementById('postPartyButton');
const clearPartyButton = document.getElementById('clearPartyButton');
const partyBoardEl = document.getElementById('partyBoard');
const communityEventsEl = document.getElementById('communityEvents');
const friendTargetInput = document.getElementById('friendTarget');
const sendFriendRequestButton = document.getElementById('sendFriendRequestButton');
const friendsListEl = document.getElementById('friendsList');
const incomingFriendRequestsEl = document.getElementById('incomingFriendRequests');
const outgoingFriendRequestsEl = document.getElementById('outgoingFriendRequests');
const raidStatusEl = document.getElementById('raidStatus');
const raidAttackButton = document.getElementById('raidAttackButton');
const raidBossNameEl = document.getElementById('raidBossName');
const raidBossBarEl = document.getElementById('raidBossBar');
const raidBossHpEl = document.getElementById('raidBossHp');
const raidRankingEl = document.getElementById('raidRanking');
const contractStatusEl = document.getElementById('contractStatus');
const contractTitleEl = document.getElementById('contractTitle');
const contractDescriptionEl = document.getElementById('contractDescription');
const contractBarEl = document.getElementById('contractBar');
const contractProgressEl = document.getElementById('contractProgress');
const contractContributeButton = document.getElementById('contractContributeButton');
const contractContributorsEl = document.getElementById('contractContributors');
const equipmentEl = document.getElementById('equipment');
const itemCatalogEl = document.getElementById('itemCatalog');
const itemSearchInput = document.getElementById('itemSearch');
const itemSlotFilter = document.getElementById('itemSlotFilter');
const itemRarityFilter = document.getElementById('itemRarityFilter');
const itemCatalogCountEl = document.getElementById('itemCatalogCount');
const hairSelect = document.getElementById('hair');
const eyesSelect = document.getElementById('eyes');
const mouthSelect = document.getElementById('mouth');
const noseSelect = document.getElementById('nose');
const earsSelect = document.getElementById('ears');
const skinToneSelect = document.getElementById('skinTone');
const startingVillageSelect = document.getElementById('startingVillage');
const duelOpponentSelect = document.getElementById('duelOpponent');
const duelButton = document.getElementById('duelButton');
const duelLogEl = document.getElementById('duelLog');
const duelLeaderboardEl = document.getElementById('duelLeaderboard');
const duelPersonalStatsEl = document.getElementById('duelPersonalStats');

let username = null;
let maxPA = 20;
let worldState = null;
let worldPositions = new Map();
let currentGuild = null;
let guildChatMessages = [];
let raidState = null;
let contractState = null;
let globalChatMessages = [];
let allItems = [];
let filteredItems = [];
let connectedPlayers = [];
let duelLeaderboard = [];
let myDuelStats = { wins: 0, losses: 0 };
let partyBoardEntries = [];
let communityEvents = [];
let socialState = { friends: [], incoming_requests: [], outgoing_requests: [] };

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
  equipment: { head: null, chest: null, weapon: 'Épée rouillée', back: 'Cape de voyage', hands: null, feet: null, trinket: null },
  profile: { hair: 'Court', eyes: 'Marron', mouth: 'Neutre', nose: 'Droit', ears: 'Rondes', skin_tone: 'Clair', starting_village: 'Village départ 1' },
  stats: { atk: 10, def: 7, vit: 6, int: 6 },
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
        globalChatMessages = [];
        partyBoardEntries = [];
        communityEvents = [];
        socialState = { friends: [], incoming_requests: [], outgoing_requests: [] };
        renderGuildStatus();
        renderGuildChat();
        renderGlobalChat();
        renderPartyBoard();
        renderCommunityEvents();
        renderFriendsPanel();
        renderRaid();
        renderContracts();
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
  hero.equipment = { ...hero.equipment, ...(serverHero.equipment || {}) };
  hero.stats = { ...hero.stats, ...(serverHero.stats || {}) };
}

function syncProfile(profile) {
  if (!profile) return;
  hero.profile = { ...hero.profile, ...profile };
}


function renderHeroStats() {
  heroStats.innerHTML = `
    <li><strong>Niveau:</strong> ${hero.level}</li>
    <li><strong>XP:</strong> ${hero.xp} / 100</li>
    <li><strong>PV:</strong> ${hero.hp} / ${hero.maxHp}</li>
    <li><strong>Or:</strong> ${hero.gold}</li>
    <li><strong>ATK:</strong> ${hero.stats.atk} | <strong>DEF:</strong> ${hero.stats.def}</li>
    <li><strong>VIT:</strong> ${hero.stats.vit} | <strong>INT:</strong> ${hero.stats.int}</li>
    <li><strong>Position:</strong> (${hero.x}, ${hero.y}) - ${hero.location}</li>
    <li><strong>Village de départ:</strong> ${hero.profile.starting_village}</li>
  `;
}

function renderEquipment() {
  if (!equipmentEl) return;
  const labels = { head: 'Tête', chest: 'Torse', weapon: 'Arme', back: 'Dos', hands: 'Mains', feet: 'Pieds', trinket: 'Artefact' };
  equipmentEl.innerHTML = '';
  Object.entries(labels).forEach(([slot,label]) => {
    const li = document.createElement('li');
    li.textContent = `${label}: ${hero.equipment[slot] || 'Aucun'}`;
    equipmentEl.appendChild(li);
  });
}

function renderCharacterPreview() {
  const container = document.getElementById('characterPreview');
  if (!container) return;
  const eye = hero.profile.eyes.toLowerCase();
  const skin = { porcelaine:'#f8e0d0', clair:'#f1c27d', doré:'#d9a066', olive:'#b68655', brun:'#8d5524', ebène:'#5a3a22' }[hero.profile.skin_tone.toLowerCase()] || '#f1c27d';
  container.innerHTML = `<div class='avatar-shell' style='background:${skin}'>
    <div class='avatar-hair'>${hero.profile.hair}</div>
    <div class='avatar-eyes'>${hero.profile.eyes}</div>
    <div class='avatar-mouth'>${hero.profile.mouth}</div>
    <div class='avatar-nose'>${hero.profile.nose}</div>
    <div class='avatar-ears'>${hero.profile.ears}</div>
    <div class='avatar-equip'>${Object.values(hero.equipment).filter(Boolean).join(' • ')}</div>
  </div>`;
}

async function equipItem(itemName) {
  if (!username) return;
  const formData = new FormData();
  formData.append('username', username);
  formData.append('item_name', itemName);
  const response = await fetch('/api/equipment/equip', { method: 'POST', body: formData });
  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Équipement impossible';
    return;
  }
  syncHero(data.hero);
  renderEquipment();
  renderCharacterPreview();
}

function renderInventory() {
  inventoryEl.innerHTML = '';
  hero.inventory.forEach((item) => {
    const li = document.createElement('li');
    const itemMeta = allItems.find((entry) => entry.name === item);
    const stats = itemMeta ? `ATK${formatSignedStat(itemMeta.atk)} DEF${formatSignedStat(itemMeta.def)} VIT${formatSignedStat(itemMeta.vit)} INT${formatSignedStat(itemMeta.int)}` : '';
    li.innerHTML = itemMeta ? `<img src='${itemMeta.image}' alt='${item}' class='inventory-icon'> <strong>${item}</strong> <small>${stats}</small>` : item;
    if (itemMeta?.slot && itemMeta.slot !== 'consumable' && username) {
      const button = buttonLabel('Équiper');
      button.addEventListener('click', async () => equipItem(item));
      li.appendChild(button);
    }
    inventoryEl.appendChild(li);
  });
}

function applyItemFilters() {
  const search = itemSearchInput?.value?.trim().toLowerCase() || '';
  const slot = itemSlotFilter?.value || 'all';
  const rarity = itemRarityFilter?.value || 'all';

  filteredItems = allItems.filter((item) => {
    const matchesSearch = !search || item.name.toLowerCase().includes(search);
    const matchesSlot = slot === 'all' || item.slot === slot;
    const matchesRarity = rarity === 'all' || item.rarity === rarity;
    return matchesSearch && matchesSlot && matchesRarity;
  });
}

function formatSignedStat(value) {
  return value >= 0 ? `+${value}` : `${value}`;
}

function rarityLabel(rarity) {
  return {
    commun: 'Commun',
    rare: 'Rare',
    epique: 'Épique',
    legendaire: 'Légendaire',
  }[rarity] || rarity;
}

function renderItemCatalog() {
  if (!itemCatalogEl) return;
  applyItemFilters();
  itemCatalogEl.innerHTML = '';

  if (itemCatalogCountEl) {
    itemCatalogCountEl.textContent = `${filteredItems.length} objet(s) affiché(s) / ${allItems.length}`;
  }

  if (!filteredItems.length) {
    const empty = document.createElement('p');
    empty.className = 'status';
    empty.textContent = 'Aucun objet pour ce filtre.';
    itemCatalogEl.appendChild(empty);
    return;
  }

  filteredItems.forEach((item) => {
    const card = document.createElement('article');
    card.className = `item-card rarity-${item.rarity}`;
    card.innerHTML = `<img src='${item.image}' alt='${item.name}'><h4>${item.name}</h4><p>${item.slot} • ${rarityLabel(item.rarity)}</p><p>ATK${formatSignedStat(item.atk)} DEF${formatSignedStat(item.def)}</p><p>VIT${formatSignedStat(item.vit)} INT${formatSignedStat(item.int)}</p>`;
    itemCatalogEl.appendChild(card);
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



function renderFriendsPanel() {
  if (!friendsListEl || !incomingFriendRequestsEl || !outgoingFriendRequestsEl) return;

  friendsListEl.innerHTML = '';
  incomingFriendRequestsEl.innerHTML = '';
  outgoingFriendRequestsEl.innerHTML = '';

  if (!username) {
    friendsListEl.innerHTML = '<li>Connectez-vous pour gérer vos alliés.</li>';
    incomingFriendRequestsEl.innerHTML = '<li>--</li>';
    outgoingFriendRequestsEl.innerHTML = '<li>--</li>';
    return;
  }

  if (!(socialState.friends || []).length) {
    friendsListEl.innerHTML = '<li>Aucun allié pour le moment.</li>';
  } else {
    socialState.friends.forEach((friend) => {
      const li = document.createElement('li');
      li.textContent = `${friend.username} — ${connectedPlayers.includes(friend.username) ? 'En ligne' : 'Hors ligne'}`;
      const removeButton = buttonLabel('Retirer');
      removeButton.addEventListener('click', async () => {
        await removeFriend(friend.username);
      });
      li.appendChild(removeButton);
      friendsListEl.appendChild(li);
    });
  }

  if (!(socialState.incoming_requests || []).length) {
    incomingFriendRequestsEl.innerHTML = '<li>Aucune invitation reçue.</li>';
  } else {
    socialState.incoming_requests.forEach((requester) => {
      const li = document.createElement('li');
      li.textContent = requester;
      const acceptButton = buttonLabel('Accepter');
      acceptButton.addEventListener('click', async () => respondFriendRequest(requester, 'accept'));
      const rejectButton = buttonLabel('Refuser');
      rejectButton.addEventListener('click', async () => respondFriendRequest(requester, 'reject'));
      li.appendChild(acceptButton);
      li.appendChild(rejectButton);
      incomingFriendRequestsEl.appendChild(li);
    });
  }

  if (!(socialState.outgoing_requests || []).length) {
    outgoingFriendRequestsEl.innerHTML = '<li>Aucune invitation en attente.</li>';
  } else {
    socialState.outgoing_requests.forEach((target) => {
      const li = document.createElement('li');
      li.textContent = `${target} (en attente)`;
      outgoingFriendRequestsEl.appendChild(li);
    });
  }
}

async function sendFriendRequest() {
  if (!username || !friendTargetInput) return;
  const target = friendTargetInput.value.trim();
  if (!target) {
    statusEl.textContent = 'Entrez un pseudo valide.';
    return;
  }

  const formData = new FormData();
  formData.append('username', username);
  formData.append('target_username', target);

  const response = await fetch('/api/friends/request', { method: 'POST', body: formData });
  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Invitation impossible.';
    return;
  }

  socialState = data.social || socialState;
  friendTargetInput.value = '';
  renderFriendsPanel();
  statusEl.textContent = data.status === 'accepted' ? `Alliance validée avec ${target}.` : `Invitation envoyée à ${target}.`;
}

async function respondFriendRequest(requester, action) {
  if (!username) return;
  const formData = new FormData();
  formData.append('username', username);
  formData.append('requester_username', requester);
  formData.append('action', action);

  const response = await fetch('/api/friends/respond', { method: 'POST', body: formData });
  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Réponse impossible.';
    return;
  }

  socialState = data.social || socialState;
  renderFriendsPanel();
  statusEl.textContent = action === 'accept' ? `Invitation de ${requester} acceptée.` : `Invitation de ${requester} refusée.`;
}

async function removeFriend(friendName) {
  if (!username) return;
  const params = new URLSearchParams({ username, target_username: friendName });
  const response = await fetch(`/api/friends?${params.toString()}`, { method: 'DELETE' });
  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Suppression impossible.';
    return;
  }

  socialState = data.social || socialState;
  renderFriendsPanel();
  statusEl.textContent = `${friendName} retiré de vos alliés.`;
}

function renderGlobalChat() {
  if (!globalChatEl) {
    return;
  }

  globalChatEl.innerHTML = '';
  if (!globalChatMessages.length) {
    globalChatEl.innerHTML = '<li>Le canal mondial est encore silencieux.</li>';
    return;
  }

  [...globalChatMessages].reverse().forEach((entry) => {
    const li = document.createElement('li');
    const time = new Date(entry.created_at).toLocaleTimeString();
    li.textContent = `[${time}] ${entry.author}: ${entry.message}`;
    globalChatEl.appendChild(li);
  });
}

function renderPartyBoard() {
  if (!partyBoardEl) {
    return;
  }

  partyBoardEl.innerHTML = '';
  if (!partyBoardEntries.length) {
    partyBoardEl.innerHTML = '<li>Aucune annonce active. Soyez le premier à recruter !</li>';
    return;
  }

  partyBoardEntries.slice(0, 12).forEach((entry) => {
    const li = document.createElement('li');
    const time = new Date(entry.created_at).toLocaleTimeString();
    const interestedCount = Number(entry.interested_count || 0);
    const isInterested = Array.isArray(entry.interested_players) && username
      ? entry.interested_players.includes(username)
      : false;

    const info = document.createElement('span');
    info.textContent = `[${time}] ${entry.author} • ${entry.activity} — ${entry.message} (intéressés: ${interestedCount})`;
    li.appendChild(info);

    if (username && entry.id) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'inline-action';
      button.textContent = isInterested ? 'Se retirer' : 'Rejoindre';
      button.addEventListener('click', async () => {
        await togglePartyInterest(entry.id);
      });
      li.appendChild(button);
    }

    partyBoardEl.appendChild(li);
  });
}

function renderCommunityEvents() {
  if (!communityEventsEl) {
    return;
  }

  communityEventsEl.innerHTML = '';
  if (!communityEvents.length) {
    communityEventsEl.innerHTML = '<li>Aucun événement marquant pour le moment.</li>';
    return;
  }

  communityEvents.slice(0, 14).forEach((entry) => {
    const li = document.createElement('li');
    const time = new Date(entry.created_at).toLocaleTimeString();
    const category = (entry.category || 'info').toUpperCase();
    li.textContent = `[${time}] [${category}] ${entry.message}`;
    communityEventsEl.appendChild(li);
  });
}

async function postPartyBoardEntry() {
  if (!username || !partyActivityInput || !partyMessageInput) {
    return;
  }

  const activity = partyActivityInput.value.trim();
  const message = partyMessageInput.value.trim();
  if (activity.length < 3) {
    statusEl.textContent = 'L\'activité doit contenir au moins 3 caractères.';
    return;
  }
  if (message.length < 6) {
    statusEl.textContent = 'Le message de recrutement doit contenir au moins 6 caractères.';
    return;
  }

  const formData = new FormData();
  formData.append('username', username);
  formData.append('activity', activity);
  formData.append('message', message);

  const response = await fetch('/api/party-board', { method: 'POST', body: formData });
  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Impossible de publier l\'annonce.';
    return;
  }

  partyBoardEntries = data.entries || [];
  partyActivityInput.value = '';
  partyMessageInput.value = '';
  renderPartyBoard();
  addLog('Annonce de groupe publiée.');
}

async function clearPartyBoardEntries() {
  if (!username) {
    return;
  }

  const response = await fetch(`/api/party-board?username=${encodeURIComponent(username)}`, { method: 'DELETE' });
  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || 'Suppression impossible.';
    return;
  }

  partyBoardEntries = data.entries || [];
  renderPartyBoard();
  addLog('Vos annonces de groupe ont été supprimées.');
}

async function togglePartyInterest(entryId) {
  if (!username) {
    return;
  }

  const formData = new FormData();
  formData.append('username', username);
  formData.append('entry_id', String(entryId));

  const response = await fetch('/api/party-board/interest', { method: 'POST', body: formData });
  const data = await response.json();
  if (!response.ok) {
    statusEl.textContent = data.error || "Impossible de mettre à jour l'annonce.";
    return;
  }

  partyBoardEntries = data.entries || [];
  renderPartyBoard();
  const label = data.action === 'added' ? 'Vous rejoignez un groupe.' : 'Vous quittez ce groupe.';
  statusEl.textContent = label;
  addLog(label);
}

async function sendGlobalMessage() {
  if (!username || !globalMessageInput) {
    return;
  }

  const content = globalMessageInput.value.trim();
  if (content.length < 2) {
    statusEl.textContent = 'Le message global doit contenir au moins 2 caractères.';
    return;
  }

  const formData = new FormData();
  formData.append('username', username);
  formData.append('message', content);

  const response = await fetch('/api/chat/global', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || 'Message global non envoyé.';
    return;
  }

  globalChatMessages = data.chat || [];
  globalMessageInput.value = '';
  renderGlobalChat();
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

function renderRaid() {
  if (!raidStatusEl || !raidBossNameEl || !raidBossBarEl || !raidBossHpEl || !raidRankingEl || !raidAttackButton) {
    return;
  }

  if (!raidState) {
    raidStatusEl.textContent = 'Raid indisponible.';
    raidBossNameEl.textContent = 'Boss inconnu';
    raidBossBarEl.style.width = '0%';
    raidBossHpEl.textContent = 'PV: -- / --';
    raidRankingEl.innerHTML = '<li>Données indisponibles.</li>';
    raidAttackButton.disabled = true;
    return;
  }

  const hpPercent = Math.max(0, Math.min(100, (raidState.hp / raidState.max_hp) * 100));
  raidBossNameEl.textContent = `${raidState.name} • Niveau ${raidState.level}`;
  raidBossBarEl.style.width = `${hpPercent}%`;
  raidBossHpEl.textContent = `PV: ${raidState.hp} / ${raidState.max_hp}`;

  raidRankingEl.innerHTML = '';
  if (!raidState.ranking?.length) {
    raidRankingEl.innerHTML = '<li>Aucune guilde n\'a encore infligé de dégâts.</li>';
  } else {
    raidState.ranking.slice(0, 8).forEach((entry, index) => {
      const li = document.createElement('li');
      li.textContent = `${index + 1}. ${entry.guild} — ${entry.damage} dégâts`;
      raidRankingEl.appendChild(li);
    });
  }

  if (!username) {
    raidStatusEl.textContent = 'Connectez-vous pour participer au raid.';
  } else if (!currentGuild) {
    raidStatusEl.textContent = 'Rejoignez une guilde pour attaquer le boss mondial.';
  } else {
    raidStatusEl.textContent = `Votre guilde ${currentGuild} peut attaquer le boss en continu.`;
  }

  raidAttackButton.disabled = !username || !currentGuild;
}

function renderContracts() {
  if (!contractStatusEl || !contractTitleEl || !contractDescriptionEl || !contractBarEl || !contractProgressEl || !contractContributorsEl || !contractContributeButton) {
    return;
  }

  if (!contractState) {
    contractStatusEl.textContent = 'Contrat indisponible.';
    contractTitleEl.textContent = 'Mission inconnue';
    contractDescriptionEl.textContent = 'Chargement...';
    contractBarEl.style.width = '0%';
    contractProgressEl.textContent = 'Progression: -- / --';
    contractContributorsEl.innerHTML = '<li>Données indisponibles.</li>';
    contractContributeButton.disabled = true;
    return;
  }

  const percent = Math.max(0, Math.min(100, (contractState.progress / contractState.goal) * 100));
  contractTitleEl.textContent = `${contractState.title} • Saison ${contractState.season}`;
  contractDescriptionEl.textContent = contractState.description;
  contractBarEl.style.width = `${percent}%`;
  contractProgressEl.textContent = `Progression: ${contractState.progress} / ${contractState.goal}`;

  if (!username) {
    contractStatusEl.textContent = 'Connectez-vous pour contribuer au contrat de saison.';
  } else {
    contractStatusEl.textContent = 'Ajoutez vos ressources pour accélérer les récompenses globales.';
  }

  contractContributeButton.disabled = !username;
  contractContributorsEl.innerHTML = '';
  if (!contractState.contributors?.length) {
    contractContributorsEl.innerHTML = "<li>Aucun contributeur pour l'instant.</li>";
    return;
  }

  contractState.contributors.slice(0, 8).forEach((entry, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${entry.username} — ${entry.points} pts`;
    contractContributorsEl.appendChild(li);
  });
}

async function refreshContracts() {
  const response = await fetch('/api/contracts/current');
  if (!response.ok) {
    return;
  }
  contractState = await response.json();
  renderContracts();
}

async function contributeContract() {
  if (!username) {
    return;
  }

  const formData = new FormData();
  formData.append('username', username);

  const response = await fetch('/api/contracts/contribute', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || 'Contribution impossible';
    return;
  }

  renderPA(data.action_points);
  syncHero(data.hero);
  renderHeroStats();
  contractState = data.contract || contractState;
  renderContracts();

  const message = data.completed
    ? `Contrat terminé ! Récompense: +${data.reward.gold} or et +${data.reward.xp} XP.`
    : `Contribution validée: +${data.contribution} progression au contrat.`;
  statusEl.textContent = message;
  addLog(message);
}

async function refreshRaid() {
  const response = await fetch('/api/raids/current');
  if (!response.ok) {
    return;
  }
  raidState = await response.json();
  renderRaid();
}

async function attackRaidBoss() {
  if (!username || !currentGuild) {
    return;
  }

  const formData = new FormData();
  formData.append('username', username);

  const response = await fetch('/api/raids/attack', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || 'Attaque impossible.';
    return;
  }

  raidState = data.raid;
  renderPA(data.action_points);
  renderRaid();

  let summary = `Vous infligez ${data.damage} dégâts au boss de raid.`;
  if (data.defeated && data.defeated_boss) {
    summary += ` ${data.defeated_boss.name} (Niv.${data.defeated_boss.level}) est vaincu ! Nouveau boss apparu.`;
  }

  statusEl.textContent = summary;
  addLog(summary);
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
  renderGlobalChat();
  renderRaid();
  renderContracts();
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
  renderGlobalChat();
  renderRaid();
  renderContracts();
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
  connectedPlayers = Object.keys(players);
  Object.entries(players).forEach(([name, state]) => {
    const li = document.createElement('li');
    li.textContent = `${name}: ${state.action_points} PA`;
    playersEl.appendChild(li);

    if (name === username) {
      renderPA(state.action_points);
    }
  });
  renderDuelOpponents();
  renderFriendsPanel();
}


function renderDuelOpponents() {
  if (!duelOpponentSelect) return;
  duelOpponentSelect.innerHTML = '';

  const opponents = connectedPlayers.filter((name) => name !== username);
  if (!opponents.length) {
    duelOpponentSelect.innerHTML = '<option value="">Aucun adversaire disponible</option>';
    duelButton.disabled = true;
    return;
  }

  opponents.forEach((name) => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    duelOpponentSelect.appendChild(opt);
  });
  duelButton.disabled = !username;
}

function renderDuelLog(entries = []) {
  if (!duelLogEl) return;
  duelLogEl.innerHTML = '';
  entries.slice(0, 8).forEach((line) => {
    const li = document.createElement('li');
    li.textContent = line;
    duelLogEl.appendChild(li);
  });
}

function renderDuelStats() {
  if (duelPersonalStatsEl) {
    duelPersonalStatsEl.textContent = `Bilan personnel: ${myDuelStats.wins} victoire(s) / ${myDuelStats.losses} défaite(s).`;
  }

  if (!duelLeaderboardEl) return;

  duelLeaderboardEl.innerHTML = '';
  if (!duelLeaderboard.length) {
    duelLeaderboardEl.innerHTML = "<li>Aucun duel classé enregistré pour l'instant.</li>";
    return;
  }

  duelLeaderboard.forEach((entry, index) => {
    const li = document.createElement('li');
    li.textContent = `${index + 1}. ${entry.username} — ${entry.wins}V / ${entry.losses}D (${entry.total} combats)`;
    duelLeaderboardEl.appendChild(li);
  });
}

async function runDuel() {
  if (!username || !duelOpponentSelect?.value) {
    statusEl.textContent = 'Aucun adversaire sélectionné.';
    return;
  }
  const formData = new FormData();
  formData.append('username', username);
  formData.append('opponent', duelOpponentSelect.value);
  const response = await fetch('/api/combat/duel', { method: 'POST', body: formData });
  const data = await response.json();

  if (!response.ok) {
    statusEl.textContent = data.error || 'Duel impossible';
    return;
  }

  renderPA(data.action_points);
  statusEl.textContent = data.summary;
  addLog(data.summary);
  renderDuelLog(data.combat.log || []);
  myDuelStats = data.duel_stats || myDuelStats;
  duelLeaderboard = data.duel_leaderboard || duelLeaderboard;
  socialState = data.social || socialState;
  renderDuelStats();
  renderFriendsPanel();
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
renderEquipment();
renderCharacterPreview();

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
renderEquipment();
renderCharacterPreview();
  renderWorld(worldState);
  renderActionPanel();

  const summary = win ? `Victoire ! +${xpGain} XP, +${goldGain} or.` : `Défaite courageuse. +${xpGain} XP, +${goldGain} or.`;
  statusEl.textContent = `${summary} ${hero.hp}/${hero.maxHp} PV.`;
  addLog(summary);
}


async function loadOptions() {
  const response = await fetch('/api/options');
  if (!response.ok) return;
  const data = await response.json();
  allItems = data.items || [];

  if (itemSlotFilter) {
    const slots = ['all', ...new Set(allItems.map((item) => item.slot))];
    itemSlotFilter.innerHTML = slots
      .map((slot) => `<option value='${slot}'>${slot === 'all' ? 'Tous les emplacements' : slot}</option>`)
      .join('');
  }

  if (itemRarityFilter) {
    const rarities = ['all', ...new Set(allItems.map((item) => item.rarity))];
    itemRarityFilter.innerHTML = rarities
      .map((rarity) => `<option value='${rarity}'>${rarity === 'all' ? 'Toutes les raretés' : rarityLabel(rarity)}</option>`)
      .join('');
  }

  renderItemCatalog();

  const mapping = { hair: hairSelect, eyes: eyesSelect, mouth: mouthSelect, nose: noseSelect, ears: earsSelect, skin_tone: skinToneSelect };
  Object.entries(mapping).forEach(([key, select]) => {
    if (!select) return;
    select.innerHTML = '';
    (data.character?.[key] || []).forEach((option) => {
      const opt = document.createElement('option');
      opt.value = option;
      opt.textContent = option;
      select.appendChild(opt);
    });
  });

  if (startingVillageSelect) {
    startingVillageSelect.innerHTML = '';
    (data.starting_villages || []).forEach((village) => {
      const opt = document.createElement('option');
      opt.value = village.name;
      opt.textContent = village.name;
      startingVillageSelect.appendChild(opt);
    });
  }
}
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'snapshot') {
    renderPlayers(data.players);
    renderGuildRanking(data.guilds || []);
    raidState = data.raid || raidState;
    contractState = data.contracts || contractState;
    duelLeaderboard = data.duels || duelLeaderboard;
    globalChatMessages = data.global_chat || globalChatMessages;
    partyBoardEntries = data.party_board || partyBoardEntries;
    communityEvents = data.events || communityEvents;
    renderRaid();
    renderContracts();
    renderGlobalChat();
    renderPartyBoard();
    renderCommunityEvents();
    renderDuelStats();
  renderFriendsPanel();
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
  globalChatMessages = data.global_chat || [];
  partyBoardEntries = data.party_board || [];
  communityEvents = data.events || [];
  myDuelStats = data.duel_stats || myDuelStats;
  duelLeaderboard = data.duel_leaderboard || duelLeaderboard;
  socialState = data.social || socialState;
  syncProfile(data.profile);

  if (data.start_position) {
    hero.x = data.start_position.x;
    hero.y = data.start_position.y;
  }
  hero.location = hero.profile.starting_village;

  renderPA(data.action_points);
  statusEl.textContent = `Bienvenue ${username}. Régénération: ${data.recharge_per_hour} PA/h.`;
  spendButton.disabled = false;
  exploreButton.disabled = false;
  quickBattleButton.disabled = false;
  renderMenu();
  renderHeroStats();
  renderEquipment();
  renderCharacterPreview();
  renderWorld(worldState);
  renderActionPanel();
  renderGuildStatus();
  renderGuildChat();
  renderGlobalChat();
  renderPartyBoard();
  renderCommunityEvents();
  renderRaid();
  renderContracts();
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
  if (duelOpponentSelect?.value) {
    await runDuel();
    return;
  }
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

sendGlobalMessageButton?.addEventListener('click', async () => {
  await sendGlobalMessage();
});

postPartyButton?.addEventListener('click', async () => {
  await postPartyBoardEntry();
});

clearPartyButton?.addEventListener('click', async () => {
  await clearPartyBoardEntries();
});

raidAttackButton?.addEventListener('click', async () => {
  await attackRaidBoss();
});

contractContributeButton?.addEventListener('click', async () => {
  await contributeContract();
});

duelButton?.addEventListener('click', async () => {
  await runDuel();
});

sendFriendRequestButton?.addEventListener('click', async () => {
  await sendFriendRequest();
});


itemSearchInput?.addEventListener('input', renderItemCatalog);
itemSlotFilter?.addEventListener('change', renderItemCatalog);
itemRarityFilter?.addEventListener('change', renderItemCatalog);

renderMenu();
renderHeroStats();
renderInventory();
renderEquipment();
renderCharacterPreview();
renderQuests();
renderActionPanel();
renderGuildStatus();
renderGuildChat();
renderGlobalChat();
renderPartyBoard();
renderCommunityEvents();
renderRaid();
renderContracts();
renderDuelOpponents();
renderDuelLog();
renderFriendsPanel();
addLog('Le portail d\'Aetheria est ouvert.');
loadOptions();
refreshWorld();
refreshGuilds();
refreshRaid();
refreshContracts();
setInterval(refreshWorld, 60000);
setInterval(refreshRaid, 15000);
setInterval(refreshContracts, 20000);
