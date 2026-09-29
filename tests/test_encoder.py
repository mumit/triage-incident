import unittest

from triage_bench.encoder import policy_guard, render_packet


class EncoderPolicyTests(unittest.TestCase):
    def packet(self, observation, edges, note='Complete upstream dependencies for the affected sites.'):
        return {
            'observations': [{'detail': observation}],
            'service_impact': {'status': 'outage', 'affected_sites': 2},
            'topology': {'edges': edges, 'note': note},
            'ticket': {'description': 'ANSWER_KEY_SENTINEL'},
        }

    def test_render_uses_current_observation_not_duplicate_ticket(self):
        packet = self.packet('Current transport counters show loss.', [['S0', 'A0']])
        text = render_packet(packet)
        self.assertIn('Current transport counters show loss.', text)
        self.assertNotIn('ANSWER_KEY_SENTINEL', text)

    def test_stale_sole_evidence_vetoes_domain_assignment(self):
        stale = self.packet('The only DC breaker observation is 75 minutes old. '
                            'Current independent domain telemetry is unavailable.', [['S0', 'A0']])
        current = self.packet('Current independent DC breaker telemetry confirms an open breaker.',
                              [['S0', 'A0']])
        self.assertEqual(policy_guard(stale, 2)[0], 4)
        self.assertEqual(policy_guard(current, 2)[0], 2)

    def test_complete_topology_vetoes_unrelated_uplink(self):
        observation = 'Current optical diagnostics confirm loss of signal at uplink A0.'
        connected = self.packet(observation, [['S0', 'A0'], ['S1', 'A0']])
        disconnected = self.packet(observation, [['S0', 'A1'], ['S1', 'A2']])
        incomplete = self.packet(observation, [['S0', 'A1']], 'Illustrative inventory excerpt.')
        missing_site = self.packet(observation, [['S0', 'A1']])
        self.assertEqual(policy_guard(connected, 1)[0], 1)
        self.assertEqual(policy_guard(disconnected, 1)[0], 4)
        self.assertEqual(policy_guard(incomplete, 1)[0], 1)
        self.assertEqual(policy_guard(missing_site, 1)[0], 1)


if __name__ == '__main__':
    unittest.main()
