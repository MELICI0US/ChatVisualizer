import json
import tempfile
import unittest
from pathlib import Path

from chat_parser import load_conversations


class LoadConversationsTests(unittest.TestCase):
    def test_parses_conversations_and_rounds(self):
        payload = {
            "conversations": {
                "group-a": {
                    "conversationId": "group-a",
                    "name": "favorite cheeses",
                    "participants": ["Swiss", "Cottage%20Cheese", "Roquefort"],
                    "messages": {
                        "m1": {
                            "body": "Let's go crazy",
                            "from": "Roquefort",
                            "runtimeType": "identified",
                            "time": "2026-09-21T18:13:47.303275Z",
                        },
                        "m2": {
                            "body": "Round 2",
                            "runtimeType": "gameNotification",
                            "time": "2026-09-21T18:15:48.882007Z",
                        },
                        "m3": {
                            "body": "Yeah let's send 5 around",
                            "from": "Roquefort",
                            "runtimeType": "identified",
                            "time": "2026-09-21T18:16:17.745874Z",
                        },
                        "m4": {
                            "body": "Round 3",
                            "runtimeType": "gameNotification",
                            "time": "2026-09-21T18:17:00.000000Z",
                        },
                    },
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "sample.json"
            file_path.write_text(json.dumps(payload), encoding="utf-8")
            conversations = load_conversations(file_path)

        self.assertEqual(len(conversations), 1)
        conversation = conversations[0]
        self.assertEqual(conversation.participants[1], "Cottage Cheese")
        self.assertIsNone(conversation.created_round)
        self.assertEqual(conversation.last_active_round, 2)
        self.assertEqual(conversation.last_active_at.isoformat(), "2026-09-21T18:16:17.745874+00:00")
        self.assertEqual(conversation.messages[0].round_number, None)
        self.assertEqual(conversation.messages[1].round_number, 2)
        self.assertEqual(conversation.messages[2].round_number, 2)
        self.assertEqual(conversation.messages[3].round_number, 3)


if __name__ == "__main__":
    unittest.main()
