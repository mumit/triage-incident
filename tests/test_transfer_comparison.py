import unittest

from scripts.analyze_transfer_comparison import compare


class TransferComparisonTests(unittest.TestCase):
    def test_missing_and_failed_predictions_count_as_wrong_in_paired_comparison(self):
        labels={'initial_owner':'ran','priority':'P3','next_check':'inspect_radio','insufficient_evidence':'no'}
        cases=[{'id':str(i),'incident_family_id':'pair-'+str(i//2),
                'accepted_answers':{k:[v] for k,v in labels.items()}} for i in range(4)]
        snapshot={'cases':cases,'runs':{
            'left':{'predictions':[{'id':'0','status':'ok','predictions':labels},
                                   {'id':'1','status':'error','predictions':labels},
                                   {'id':'3','status':'ok','predictions':labels}]},
            'right':{'predictions':[{'id':'0','status':'ok','predictions':labels},
                                    {'id':'1','status':'ok','predictions':labels},
                                    {'id':'2','status':'error'}]}}}
        result=compare(snapshot,'left','right')
        self.assertEqual(result['counts'],{'both_correct':1,'right_only_correct':1,'both_wrong':1,'left_only_correct':1})
        self.assertEqual(result['left_minus_right_agreement'],0)
        self.assertEqual(result['families'],2)
        self.assertEqual(result['incident_mcnemar_exact_two_sided_p'],1)
