import math
import unittest

from scripts.build_oracle_replay import distance_to_reference, geometric_deviation, review_start, walk_edges, yaw_wxyz


class OracleReplayTests(unittest.TestCase):
    def test_teleport_same_action_is_never_a_walk(self):
        nodes = [dict(a=11, segment=0), dict(a=12, segment=0), dict(a=12, segment=1), dict(a=13, segment=1)]
        self.assertEqual(walk_edges(nodes), [(0, 1), (2, 3)])

    def test_distance_projects_onto_segments_and_ignores_height(self):
        self.assertAlmostEqual(distance_to_reference([5, 1, -9], [[0, 0, 1], [0, 0, 1], [10, 0, 1]]), 1)

    def test_wxyz_orientation_and_unknown_terminal_pose(self):
        self.assertAlmostEqual(yaw_wxyz([math.sqrt(.5), 0, 0, math.sqrt(.5)]), math.pi / 2)
        self.assertIsNone(yaw_wxyz(None))

    def test_recorded_interval_is_not_replaced_by_closest_point(self):
        nodes = [dict(a=i, p=[i, 0]) for i in range(13)]
        start, basis = review_start(nodes, 12, 0, [11, 0], '第 8 至 12 动作持续向北进入错误过道。')
        self.assertEqual(start, 8)
        self.assertIn('不是精确错误起始', basis)

    def test_estimate_cannot_cross_a_previous_teleport(self):
        nodes = [dict(a=i, p=p) for i, p in enumerate([[0, 0], [9, 0], [5, 0], [2, 0], [3, 0], [5, 0]])]
        start, basis = review_start(nodes, 5, 2, [0, 0], '返回这个路口。')
        self.assertEqual(start, 3)
        self.assertIn('估计', basis)

    def test_geometric_hint_requires_three_records_in_same_leg(self):
        nodes = [dict(distance=.8, segment=0), dict(distance=.9, segment=0), dict(distance=1., segment=1)]
        self.assertIsNone(geometric_deviation(nodes))
        nodes.append(dict(distance=.9, segment=1))
        self.assertIsNone(geometric_deviation(nodes))
        nodes.append(dict(distance=.9, segment=1))
        self.assertEqual(geometric_deviation(nodes), 2)


if __name__ == '__main__':
    unittest.main()
