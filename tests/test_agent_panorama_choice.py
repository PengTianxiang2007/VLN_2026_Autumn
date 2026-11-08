"""Evidence isolation and exclusions, independent of model execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from core.agent_route_choice import file_hash
from core.agent_panorama_choice import build_messages, validate_inventory, validate_choice


class PanoramaContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root = Path(self.tmp.name)
        (self.root / 'rgb.png').write_bytes(b'fixture-only'); sha = file_hash(self.root / 'rgb.png')
        images = [dict(id=f'V{i}', yaw_deg=i*45, phase='crossing_panorama', path='rgb.png', sha256=sha) for i in range(8)]
        images += [dict(id=f'F{i:04d}', frame=i, phase='approach_history' if i <= 3 else 'wrong_attempt', path='rgb.png', sha256=sha) for i in range(8)]
        self.case = dict(sample_id='sample_01', instruction='Go through the doorway.', checkpoint_frame=3, wrong_end_frame=7, images=images,
                         approach_actions=[dict(frame=i, action='FORWARD') for i in range(3)], attempt_actions=[dict(frame=i, action='LEFT') for i in range(3,7)])
        self.inv = dict(view_summary='Three openings.', branches=[dict(id=f'B{i}', direction=d, landmark='Doorway', destination_hypothesis='Room',
                        panorama_view_ids=[v], evidence_ids=[v], incoming='yes' if i == 1 else 'no') for i,d,v in [(1,'front','V0'),(2,'left','V2'),(3,'right','V6')]],
                        incoming_branch_id='B1', incoming_evidence_ids=['V0','F0000'], incoming_reason='Approach match.', coverage='complete', uncertainties=[])
        self.choice = dict(status='selected', wrong_branch_id='B2', wrong_branch_evidence_ids=['V2','F0007'], error_reason='Wrong room.',
                           incoming_branch_id='B1', incoming_evidence_ids=['V0','F0000'], incoming_reason='Approach match.', excluded_branch_ids=['B1','B2'],
                           instruction_evidence=['Go through the doorway.'], selected_branch_id='B3', selected_direction='right', selected_panorama_view_ids=['V6'],
                           route_description='Go right.', selection_evidence_ids=['V6'], confidence='medium', uncertainties=[])

    def test_first_call_isolation_and_second_call_full_inventory(self):
        one = build_messages(self.case, self.root, 1, 'inventory', embed=False)
        metadata = json.loads(one[1]['content'][0]['text'])
        self.assertNotIn('instruction', metadata); self.assertNotIn('branch_inventory', metadata)
        self.assertEqual(sum(x['type']=='image_url' for x in one[1]['content']), 12)
        self.assertNotIn('wrong_attempt', json.dumps(one))
        two = build_messages(self.case, self.root, 2, 'choose', self.inv, embed=False)
        self.assertEqual([m['role'] for m in two], ['system','user'])
        self.assertEqual(json.loads(two[1]['content'][0]['text'])['branch_inventory'], self.inv)
        self.assertEqual(sum(x['type']=='image_url' for x in two[1]['content']), 16)

    def test_reject_extra_metadata_and_changed_rgb(self):
        for key in ('map','expected_route','position'):
            c = dict(self.case, **{key:'forbidden'})
            with self.assertRaises(ValueError): build_messages(c,self.root,1,'prompt')
        (self.root/'rgb.png').write_bytes(b'mutated')
        with self.assertRaises(ValueError): build_messages(self.case,self.root,1,'prompt')

    def test_both_exclusions_required(self):
        validate_choice(self.choice,self.inv,self.case)
        for wrong in (['B2'],['B1'],['B1','B2','B3']):
            a=dict(self.choice,excluded_branch_ids=wrong)
            with self.assertRaises(ValueError): validate_choice(a,self.inv,self.case)

    def test_cannot_select_wrong_or_incoming(self):
        for bid in ('B1','B2','B9'):
            with self.assertRaises(ValueError): validate_choice(dict(self.choice,selected_branch_id=bid),self.inv,self.case)

    def test_deduplicate_same_incoming_wrong(self):
        a=dict(self.choice,wrong_branch_id='B1',excluded_branch_ids=['B1'])
        validate_choice(a,self.inv,self.case)

    def test_incoming_requires_both_visual_phases(self):
        validate_inventory(self.inv,self.case)
        for ev in (['V0'],['F0000']):
            with self.assertRaises(ValueError): validate_inventory(dict(self.inv,incoming_evidence_ids=ev),self.case)
            with self.assertRaises(ValueError): validate_choice(dict(self.choice,incoming_evidence_ids=ev),self.inv,self.case)

    def test_no_direction_rewrite_or_false_instruction_quote(self):
        for change in (dict(selected_direction='left'),dict(instruction_evidence=['Turn right.']),dict(selected_panorama_view_ids=['V2'])):
            with self.assertRaises(ValueError): validate_choice(dict(self.choice,**change),self.inv,self.case)

    def test_abstention_preserves_exclusions(self):
        a=dict(self.choice,status='insufficient_evidence',selected_branch_id=None,selected_direction=None,selected_panorama_view_ids=[],selection_evidence_ids=[],uncertainties=['Ambiguous destination.'])
        validate_choice(a,self.inv,self.case)
        with self.assertRaises(ValueError): validate_choice(dict(a,uncertainties=[]),self.inv,self.case)

    def test_empty_route_is_allowed_only_when_no_route_selected(self):
        a=dict(self.choice,status='insufficient_evidence',selected_branch_id=None,selected_direction=None,
               selected_panorama_view_ids=[],selection_evidence_ids=[],uncertainties=['No eligible route.'],route_description='')
        validate_choice(a,self.inv,self.case)
        with self.assertRaises(ValueError): validate_choice(dict(self.choice,route_description=''),self.inv,self.case)


if __name__ == '__main__': unittest.main()
