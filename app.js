const fileInput = document.getElementById("fileInput");
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const eventsEl = document.getElementById("events");
const conversationsEl = document.getElementById("conversations");

fileInput.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  try {
    const text = await file.text();
    const data = JSON.parse(text);
    const normalized = normalizeData(data);
    render(normalized);
  } catch (error) {
    clearView();
    statusEl.textContent = `Unable to parse JSON: ${error.message}`;
  }
});

function normalizeData(rawData) {
  const flattened = flattenMessages(rawData);
  const players = collectPlayers(rawData, flattened);
  const chats = buildChats(flattened);

  return { players, chats };
}

function flattenMessages(rawData) {
  const messages = [];
  if (Array.isArray(rawData.messages)) {
    rawData.messages.forEach((message, index) => {
      messages.push(normalizeMessage(message, index));
    });
  }

  if (Array.isArray(rawData.conversations)) {
    rawData.conversations.forEach((conversation, conversationIndex) => {
      const conversationMessages = Array.isArray(conversation.messages) ? conversation.messages : [];
      conversationMessages.forEach((message, messageIndex) => {
        messages.push(
          normalizeMessage(message, `${conversationIndex}-${messageIndex}`, {
            participants:
              toStringArray(conversation.participants) ||
              toStringArray(conversation.members) ||
              toStringArray(conversation.players),
            conversationId: conversation.id || conversation.conversationId || conversation.chatId,
          }),
        );
      });
    });
  }

  return messages;
}

function normalizeMessage(message, order, inherited = {}) {
  const sender = firstString(message.sender, message.from, message.player, message.author);
  const text = firstString(message.text, message.message, message.content) || "";
  const roundRaw = message.round ?? message.turn;
  const round = Number.isFinite(Number(roundRaw)) ? Number(roundRaw) : null;

  const explicitParticipants =
    toStringArray(message.participants) ||
    toStringArray(message.members) ||
    toStringArray(message.players) ||
    toStringArray(message.recipients) ||
    toStringArray(message.to) ||
    toStringArray(message.groupMembers);
  let participants = explicitParticipants || inherited.participants || [];
  if (sender && !participants.includes(sender)) {
    participants = [...participants, sender];
  }

  const chatId =
    firstString(message.groupId, message.chatId, message.conversationId) || inherited.conversationId || null;

  return {
    sender: sender || "Unknown",
    text,
    round,
    timestamp: firstString(message.timestamp, message.time, message.createdAt),
    participants: uniqueSorted(participants),
    chatId,
    order,
  };
}

function collectPlayers(rawData, messages) {
  const fromRoot =
    toStringArray(rawData.players) || toStringArray(rawData.playerNames) || toStringArray(rawData.participants) || [];
  const fromMessages = new Set(fromRoot);
  messages.forEach((message) => {
    fromMessages.add(message.sender);
    message.participants.forEach((participant) => fromMessages.add(participant));
  });
  return [...fromMessages].filter(Boolean).sort();
}

function buildChats(messages) {
  const map = new Map();
  messages.forEach((message, index) => {
    const key = buildChatKey(message, index);
    if (!map.has(key)) {
      map.set(key, {
        key,
        participants: message.participants,
        messages: [],
        createdRound: null,
        lastUsedRound: null,
        createdOrder: null,
        lastUsedOrder: null,
      });
    }

    const chat = map.get(key);
    chat.messages.push(message);
    const roundValue = message.round ?? Number.MAX_SAFE_INTEGER;

    if (
      chat.createdOrder === null ||
      roundValue < (chat.createdRound ?? Number.MAX_SAFE_INTEGER) ||
      (roundValue === chat.createdRound && String(message.order) < String(chat.createdOrder))
    ) {
      chat.createdRound = message.round;
      chat.createdOrder = message.order;
    }

    if (
      chat.lastUsedOrder === null ||
      roundValue > (chat.lastUsedRound ?? Number.MIN_SAFE_INTEGER) ||
      (roundValue === chat.lastUsedRound && String(message.order) > String(chat.lastUsedOrder))
    ) {
      chat.lastUsedRound = message.round;
      chat.lastUsedOrder = message.order;
    }
  });

  const chats = [...map.values()];
  chats.forEach((chat) => {
    chat.messages.sort(compareMessages);
  });
  chats.sort(compareChats);
  return chats;
}

function buildChatKey(message, index) {
  if (message.chatId) {
    return `id:${message.chatId}`;
  }
  if (message.participants.length > 0) {
    return `p:${message.participants.join("|")}`;
  }
  return `m:${index}`;
}

function compareMessages(a, b) {
  const roundA = a.round ?? Number.MAX_SAFE_INTEGER;
  const roundB = b.round ?? Number.MAX_SAFE_INTEGER;
  if (roundA !== roundB) {
    return roundA - roundB;
  }
  return String(a.order).localeCompare(String(b.order), undefined, { numeric: true });
}

function compareChats(a, b) {
  const createdA = a.createdRound ?? Number.MAX_SAFE_INTEGER;
  const createdB = b.createdRound ?? Number.MAX_SAFE_INTEGER;
  if (createdA !== createdB) {
    return createdA - createdB;
  }
  return a.participants.join("|").localeCompare(b.participants.join("|"));
}

function render({ players, chats }) {
  clearView();
  statusEl.textContent = "Loaded JSON successfully.";

  const summary = document.createElement("p");
  summary.textContent = `Players: ${players.length} (${players.join(", ") || "none"}). Chats: ${chats.length}.`;
  summaryEl.appendChild(summary);

  const eventHeader = document.createElement("h2");
  eventHeader.textContent = "Chat Lifecycle";
  eventsEl.appendChild(eventHeader);

  const eventList = document.createElement("ul");
  eventList.className = "event-list";
  chats.forEach((chat) => {
    const li = document.createElement("li");
    li.textContent = `${chatLabel(chat)} — Created ${roundLabel(chat.createdRound)}, last used ${roundLabel(
      chat.lastUsedRound,
    )}`;
    eventList.appendChild(li);
  });
  eventsEl.appendChild(eventList);

  const conversationHeader = document.createElement("h2");
  conversationHeader.textContent = "Conversations";
  conversationsEl.appendChild(conversationHeader);

  const conversationList = document.createElement("div");
  conversationList.className = "chat-list";
  chats.forEach((chat) => {
    const card = document.createElement("article");
    card.className = "chat-card";

    const title = document.createElement("h3");
    title.textContent = chatLabel(chat);
    card.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "chat-meta";
    meta.appendChild(createBadge(`Created: ${roundLabel(chat.createdRound)}`));
    meta.appendChild(createBadge(`Last used: ${roundLabel(chat.lastUsedRound)}`));
    card.appendChild(meta);

    const messages = document.createElement("ul");
    messages.className = "message-list";
    chat.messages.forEach((message) => {
      const item = document.createElement("li");
      item.className = "message-item";
      if (message.order === chat.createdOrder) {
        item.classList.add("create-event");
      }
      if (message.order === chat.lastUsedOrder) {
        item.classList.add("retire-event");
      }

      const header = document.createElement("div");
      header.className = "message-header";
      header.textContent = `${roundLabel(message.round)} • ${message.sender}`;

      const text = document.createElement("div");
      text.className = "message-text";
      text.textContent = message.text || "(empty message)";

      item.appendChild(header);
      item.appendChild(text);
      messages.appendChild(item);
    });
    card.appendChild(messages);
    conversationList.appendChild(card);
  });

  conversationsEl.appendChild(conversationList);
}

function roundLabel(round) {
  return round === null || round === undefined ? "Round unknown" : `Round ${round}`;
}

function chatLabel(chat) {
  return chat.participants.length > 0 ? chat.participants.join(", ") : "Unscoped chat";
}

function createBadge(text) {
  const span = document.createElement("span");
  span.className = "badge";
  span.textContent = text;
  return span;
}

function clearView() {
  summaryEl.textContent = "";
  eventsEl.textContent = "";
  conversationsEl.textContent = "";
}

function toStringArray(value) {
  if (!Array.isArray(value)) {
    return null;
  }
  return value.map((entry) => String(entry)).filter(Boolean);
}

function firstString(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && value !== "") {
      return String(value);
    }
  }
  return null;
}

function uniqueSorted(values) {
  return [...new Set(values)].sort();
}
