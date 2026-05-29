import unittest

from app.risk import ResidentSnapshot, build_shift_digest, score_resident


class RiskEngineTest(unittest.TestCase):
    def test_stable_resident_has_low_score(self):
        result = score_resident(
            ResidentSnapshot(
                name="Joao",
                age=76,
                systolic=126,
                diastolic=78,
                pain_score=1,
                glucose=112,
                fall_risk=2,
                hydration_ml=1600,
                mood="tranquilo",
            )
        )

        self.assertEqual(result["level"], "estavel")
        self.assertLess(result["score"], 42)

    def test_multiple_alerts_raise_priority(self):
        result = score_resident(
            ResidentSnapshot(
                name="Helena",
                age=90,
                systolic=176,
                diastolic=106,
                pain_score=8,
                glucose=230,
                fall_risk=9,
                hydration_ml=700,
                mood="confuso",
            )
        )

        self.assertEqual(result["level"], "critico")
        self.assertGreaterEqual(result["score"], 70)
        self.assertTrue(any("pressao" in reason for reason in result["reasons"]))

    def test_shift_digest_includes_tasks_and_meds(self):
        resident = {"id": 1, "name": "Helena Matos", "age": 84, "room": "B-12"}
        risk = {"level": "observacao", "score": 55, "reasons": ["pressao em observacao"], "actions": []}
        digest = build_shift_digest(
            resident,
            risk,
            [{"title": "Reavaliar pressao", "status": "pending"}],
            [{"name": "Losartana", "dose": "50mg", "next_at": "10:30", "status": "scheduled"}],
            [{"note": "PA elevada em primeira afericao"}],
        )

        self.assertIn("Helena Matos", digest["summary"])
        self.assertIn("Losartana", digest["summary"])
        self.assertIn("Reavaliar pressao", digest["summary"])


if __name__ == "__main__":
    unittest.main()
