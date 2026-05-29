from pathlib import Path
import tempfile
import unittest

from app import database


class DatabaseTest(unittest.TestCase):
    def test_seed_dashboard_and_task_toggle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "gericare.sqlite3")
            database.init_database(db_path, auto_seed=True)

            data = database.dashboard(db_path)
            self.assertEqual(data["metrics"]["residents"], 4)
            self.assertGreaterEqual(data["metrics"]["pending_tasks"], 1)

            task = data["tasks"][0]
            updated = database.toggle_task(db_path, task["id"])
            self.assertIsNotNone(updated)
            self.assertNotEqual(task["status"], updated["status"])

    def test_export_contains_risk_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "gericare.sqlite3")
            database.init_database(db_path, auto_seed=True)

            csv_content = database.export_residents_csv(db_path)
            self.assertIn("risk_level", csv_content)
            self.assertIn("Helena Matos", csv_content)

    def test_support_tables_include_family_visits_and_care_plans(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "gericare.sqlite3")
            database.init_database(db_path, auto_seed=True)

            data = database.dashboard(db_path)

            self.assertGreaterEqual(data["metrics"]["family_contacts"], 4)
            self.assertGreaterEqual(data["metrics"]["emergency_contacts"], 1)
            self.assertTrue(data["visits"])
            self.assertTrue(data["care_plans"])

    def test_digest_includes_reference_family_contact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "gericare.sqlite3")
            database.init_database(db_path, auto_seed=True)

            digest = database.resident_digest(db_path, 1)

            self.assertIsNotNone(digest)
            self.assertTrue(any("familiar de referencia" in action for action in digest["actions"]))


if __name__ == "__main__":
    unittest.main()
