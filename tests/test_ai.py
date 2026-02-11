import unittest
import sys
import os

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai import FernAI

class TestAI(unittest.TestCase):
    def setUp(self):
        # We need to mock things if we don't want to load LLMs
        # but for now let's just see if it initializes
        pass

    def test_engagement_self(self):
        ai = FernAI()
        # Mock triggers and handle
        ai.bot_handle = "@fern"
        ai.bot_name = "Fern"
        
        should, reason = ai.analyze_engagement("Fern", "hi")
        self.assertFalse(should)
        self.assertEqual(reason, "Self")

    def test_engagement_mention(self):
        ai = FernAI()
        ai.triggers = ["fern"]
        ai.last_reply_time = 0
        
        should, reason = ai.analyze_engagement("User", "hey fern")
        self.assertTrue(should)
        self.assertEqual(reason, "Direct Mention")

if __name__ == '__main__':
    unittest.main()
