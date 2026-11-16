"""
Unit tests for Dataset Loaders and Manifest Generation (Section 7)
"""

import unittest
import os
import json

from datasets_loader import (
    MMLU_CORE_DOMAINS,
    load_dataset_manifest,
    create_frozen_manifests,
)


class TestDatasetsLoader(unittest.TestCase):

    def test_1_mmlu_domains_defined(self):
        self.assertEqual(len(MMLU_CORE_DOMAINS), 5)
        self.assertIn("formal_logic", MMLU_CORE_DOMAINS)
        self.assertIn("college_physics", MMLU_CORE_DOMAINS)
        self.assertIn("machine_learning", MMLU_CORE_DOMAINS)
        self.assertIn("moral_scenarios", MMLU_CORE_DOMAINS)
        self.assertIn("us_foreign_policy", MMLU_CORE_DOMAINS)

    def test_2_load_camera_tasks(self):
        items = load_dataset_manifest("camera")
        self.assertGreaterEqual(len(items), 3)
        self.assertIn("Sony Alpha", items[0]["product"])

    def test_3_load_gsm8k_and_math(self):
        gsm_items = load_dataset_manifest("gsm8k", max_samples=2)
        self.assertGreaterEqual(len(gsm_items), 2)
        self.assertIn("ground_truth", gsm_items[0])

        math_items = load_dataset_manifest("math", max_samples=2)
        self.assertGreaterEqual(len(math_items), 2)

    def test_4_load_wikiqa(self):
        wiki_items = load_dataset_manifest("wikiqa")
        self.assertGreaterEqual(len(wiki_items), 2)
        self.assertIn("candidate_sentences", wiki_items[0])

    def test_5_frozen_manifests_integrity(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        m_dir = os.path.join(base_dir, "manifests")
        # Check that files exist and are valid JSON
        for d in MMLU_CORE_DOMAINS:
            p = os.path.join(m_dir, f"manifest_mmlu_{d}.json")
            self.assertTrue(os.path.exists(p), f"Missing {p}")
            with open(p) as f:
                data = json.load(f)
                self.assertGreater(len(data), 0)


if __name__ == "__main__":
    unittest.main()

