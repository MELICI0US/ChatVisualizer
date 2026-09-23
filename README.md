# ChatVisualizer

Simple UI explorer for Junior High Game chat logs.

## Usage

1. Open `/home/runner/work/ChatVisualizer/ChatVisualizer/index.html` in a browser.
2. Upload a JSON file from the game.
3. The app will:
   - Show detected players
   - Render all conversations grouped by chat participants
   - Highlight when each chat is created (first used) and when it stops being used (last used)

## Expected JSON shape

The viewer is intentionally flexible. It can read common fields like:

- Root:
  - `players` or `playerNames`
  - `messages` (flat list), or `conversations` (with nested `messages`)
- Message fields (any of these aliases):
  - Sender: `sender`, `from`, `player`, `author`
  - Text: `text`, `message`, `content`
  - Round: `round`, `turn`
  - Participants: `participants`, `members`, `players`, `recipients`, `to`, `groupMembers`
  - Chat id: `groupId`, `chatId`, `conversationId`