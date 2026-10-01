# ChatVisualizer

Small Python UI explorer for Junior High Game chat exports.

## Run

```bash
python chat_visualizer.py
```

Then click **Open JSON** and pick a chat export file.

After opening an export, select each conversation and choose why it was created
or why it stopped getting used from the dropdown (for example,
`random initial group` or `teammate left`). Choose **Other** to type a custom
reason. Press **Enter** or click **Save Reasons** to save the creation notes in
`<export-name>.reasons.json` and stopped-use notes in
`<export-name>.stopped_reasons.json`, separately from the export. Existing
notes are loaded automatically when the export is opened again.

Creation dropdown options are loaded from [common_reasons.json](common_reasons.json),
and stopped-use dropdown options are loaded from
[common_stopped_reasons.json](common_stopped_reasons.json).
To add reasons used in existing annotation files, run:

```bash
python update_common_reasons.py
```

The command scans recursively for `*.reasons.json` and
`*.stopped_reasons.json` files and updates their respective common-reasons
files. Pass a directory to scan another location, such as
`python update_common_reasons.py path/to/annotated/files`.

## What it shows

- All conversations, creators, and participants
- Color-coded player names in the conversation details
- Number of messages sent by players in each conversation
- When each conversation was first created and when a player last sent a message
- Round markers inferred from `gameNotification` messages (for example, "Round 2")
- Full conversation transcript with round-highlighted sections
- Conversation creation and stopped-use reasons stored separately from the chat export
