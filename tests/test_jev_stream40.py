"""CPU checks for the causal N=11 JEV streaming runner."""
import importlib.util
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'run_jev_noul_v004_40_stream',
    ROOT / 'scripts/run_jev_noul_v004_40_stream.py',
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StreamingProminenceTest(unittest.TestCase):
    def values(self):
        return [
            0.05, 0.08, 0.12, 0.22, 0.48, 0.67, 0.55, 0.31, 0.20,
            0.12, 0.52, 0.61, 0.58, 0.50, 0.47, 0.29, 0.19, 0.09,
            0.15, 0.57, 0.73, 0.64, 0.32, 0.21, 0.10, 0.05, 0.03,
        ]

    def test_online_values_match_batch_reference_at_each_prefix(self):
        values = self.values()
        reference = MODULE.offline_streaming_prominence(
            values, MODULE.WINDOW_N, MODULE.MAX_DELAY_STEPS
        )
        online = MODULE.OnlineProminence(
            MODULE.WINDOW_N, MODULE.MAX_DELAY_STEPS
        )
        for _ in values:
            online.add_pending()
        for index, value in enumerate(values):
            online.resolve(index, value)
            for frozen in range(online.next_freeze):
                self.assertTrue(
                    math.isclose(
                        online.out[frozen],
                        reference[frozen],
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    )
                )
        online.finish()
        for actual, expected in zip(online.out, reference):
            self.assertTrue(
                math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
            )

    def test_online_nodes_are_frozen_within_delay(self):
        values = self.values()
        online = MODULE.OnlineProminence(
            MODULE.WINDOW_N, MODULE.MAX_DELAY_STEPS
        )
        for _ in values:
            online.add_pending()
        for index, value in enumerate(values):
            before = list(online.nodes)
            online.resolve(index, value)
            self.assertEqual(online.nodes[:len(before)], before)
        online.finish()
        self.assertTrue(all(
            node['lag_steps'] <= MODULE.MAX_DELAY_STEPS
            for node in online.nodes
        ))
        self.assertLessEqual(
            online.max_node_lag, MODULE.MAX_DELAY_STEPS
        )

    def test_runner_parameters_match_requested_pipeline(self):
        self.assertEqual(MODULE.EXPECTED_EPISODES, 40)
        self.assertEqual(MODULE.SHARD_COUNT, 2)
        self.assertEqual(MODULE.WINDOW_N, 11)
        self.assertEqual(MODULE.MAX_DELAY_STEPS, 5)
        self.assertEqual(MODULE.MAX_IN_FLIGHT, 5)


if __name__ == '__main__':
    unittest.main()
