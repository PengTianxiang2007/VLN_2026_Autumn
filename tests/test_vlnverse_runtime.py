import unittest
from core.vlnverse_runtime import placement, retry_delay, failure_kind

class RuntimeTests(unittest.TestCase):
    def test_large_scene_separates_gpus_and_reserves_simulator_headroom(self):
        rows=[dict(index=0,free_mib=42000,utilization=0),dict(index=3,free_mib=48500,utilization=0)]
        self.assertEqual(placement(rows,[3,0],set(),True),(0,3))
        self.assertIsNone(placement(rows,[3,0],{0},True))
        self.assertIsNone(placement(rows,[3],set(),True))
        rows[1]['utilization']=100
        self.assertIsNone(placement(rows,[3,0],set(),True))

    def test_normal_scene_respects_busy_cards_and_free_memory(self):
        rows=[dict(index=0,free_mib=42000,utilization=0),dict(index=3,free_mib=33000,utilization=0)]
        self.assertEqual(placement(rows,[3,0],set()),(0,0))
        self.assertIsNone(placement(rows,[3,0],{0}))

    def test_retry_only_infrastructure_errors_with_finite_budget(self):
        self.assertEqual(failure_kind('VkResult: ERROR_OUT_OF_DEVICE_MEMORY'),'gpu_oom')
        self.assertEqual(failure_kind('Model loading timeout'),'model_startup_timeout')
        for kind in ('gpu_oom','model_startup_timeout','gpu_admission'):
            self.assertEqual([retry_delay(kind,n) for n in (1,2,3,4)],[60,120,240,None])
        self.assertIsNone(retry_delay(failure_kind('Invalid episode ID'),1))
        self.assertIsNone(retry_delay(failure_kind("TypeError: NoneType memory"),1))
