"""Authored scenario families. Related realizations never cross a split."""
# split | family | owner | next check | uncertain | status | observations
CATALOG = '''train|radio_load|ran|inspect_radio|no|degraded|Busy-hour radio resource utilization is 97%; backhaul utilization is 31%. Radio scheduling delay increased with demand.
train|radio_interference|ran|inspect_radio|no|degraded|Uplink noise floor rose 12 dB across adjacent sectors. Transport loss and latency are unchanged.
train|radio_antenna|ran|inspect_radio|no|degraded|Antenna branch imbalance is 9 dB on one sector. Other sectors and the site uplink remain healthy.
train|radio_handover|ran|inspect_radio|no|degraded|Handover failures increased only between two neighboring cells. Sessions that remain on either cell are stable.
train|radio_sync|ran|inspect_radio|no|degraded|The radio timing receiver lost satellite lock; transport timing and packet delivery remain healthy. Radio timing holdover is expiring.
train|radio_carrier|ran|inspect_radio|no|degraded|One radio carrier is unavailable while other carriers at the same site carry traffic normally. No site power or transport alarm is active.
validation|radio_scheduler|ran|inspect_radio|no|degraded|Scheduling delay is elevated despite low resource occupancy. The radio scheduler reports repeated task stalls; the site uplink is healthy.
validation|radio_receiver|ran|inspect_radio|no|degraded|Receive sensitivity worsened on one radio branch after heavy rain. No optical or power change is observed.
test|radio_pim|ran|inspect_radio|no|degraded|Uplink interference tracks downlink transmit power on one sector. The shared transport path has clean counters and normal latency.
test|radio_neighbor|ran|inspect_radio|no|degraded|Mobility failures are restricted to a newly introduced neighbor relation. Stationary sessions and transport probes succeed.
train|transport_los|transport|inspect_transport|no|outage|The shared aggregation uplink reports optical loss of signal. Downstream sites became unreachable within 90 seconds; their independent power telemetry is normal.
train|transport_congestion|transport|inspect_transport|no|degraded|Aggregation egress utilization is 99% with queue drops. Radio resource utilization is 35%; affected sites share that egress.
train|transport_flap|transport|inspect_transport|no|degraded|The aggregation adjacency resets every 40 seconds. Service interruptions align with those resets; radio processes stay healthy.
train|transport_crc|transport|inspect_transport|no|degraded|CRC errors rise on a shared Ethernet span. Packet loss is visible across that span but not on its ingress segment.
train|transport_mtu|transport|inspect_transport|no|degraded|Small probes pass but larger non-fragmenting probes fail on the common backhaul path. Radio scheduling and power remain normal.
train|transport_lag|transport|inspect_transport|no|degraded|A member of the shared link aggregation group drops frames. Flows using other members succeed, and radio KPIs outside those flows are stable.
validation|transport_route|transport|inspect_transport|no|outage|The common aggregation router has withdrawn the downstream site prefixes. Links remain up, and independent site power telemetry is normal.
validation|transport_optics|transport|inspect_transport|no|degraded|Receive optical power on the aggregation span declined by 8 dB from its own baseline while frame errors increased. Radio alarms follow the packet loss.
test|transport_qos|transport|inspect_transport|no|degraded|Only the expedited forwarding queue drops traffic on the common uplink. Other classes succeed and radio resource occupancy is normal.
test|transport_asymmetry|transport|inspect_transport|no|degraded|Bidirectional probes show loss only on the return aggregation path. Radio processing and the outbound transport path are healthy.
train|power_mains|power|inspect_power|no|degraded|The site mains supply failed and batteries are discharging. Transport and radio hardware have no independent fault indication.
train|power_rectifier|power|inspect_power|no|degraded|Two rectifier modules failed; DC voltage is declining. Radio and transport alarms began after the voltage decline.
train|power_exhausted|power|inspect_power|no|outage|Independent power telemetry reports battery exhaustion after mains failure. Radio and transport equipment at the affected site stopped simultaneously.
train|power_breaker|power|inspect_power|no|outage|The equipment DC branch breaker is open. The upstream transport node is reachable and other powered branches remain healthy.
train|power_generator|power|inspect_power|no|degraded|The standby generator failed its start sequence during a mains outage. Equipment is still operating on batteries.
train|power_dc|power|inspect_power|no|degraded|DC supply voltage repeatedly drops below the equipment operating range. Radio resets align with the voltage dips, not with transport events.
validation|power_transfer|power|inspect_power|no|outage|Utility supply is healthy but the transfer switch has not connected it to the equipment bus. The bus reports no voltage.
validation|power_battery|power|inspect_power|no|degraded|The battery string reports a disconnected interconnect during mains failure. The remaining string is discharging faster than planned.
test|power_fuse|power|inspect_power|no|outage|A blown DC distribution fuse isolates the radio and site router. Independent upstream probes show the aggregation node is healthy.
test|power_controller|power|inspect_power|no|degraded|The power controller repeatedly opens the DC contactor despite healthy mains. Equipment resets align with the contactor events.
train|core_registration|core|inspect_core|no|degraded|Registration rejects increased across sites on independent transport paths. The mobility service reports internal request failures; radio admission remains normal.
train|core_sessions|core|inspect_core|no|degraded|Session establishment fails across unrelated sites. The session service reports exhausted worker capacity while transport probes succeed.
train|core_upf|core|inspect_core|no|outage|Sessions using one user-plane pool cannot pass traffic. Other pools on the same radio and transport paths work normally.
train|core_auth|core|inspect_core|no|degraded|Authentication requests time out across independent access paths. The authentication service reports unavailable database connections.
train|core_dns|core|inspect_core|no|degraded|The operator resolver service times out across unrelated access paths. Direct address connectivity works and its service health check fails.
train|core_policy|core|inspect_core|no|degraded|Policy-control requests fail for sessions across several access paths. Core service logs show an internal policy-store error.
validation|core_address|core|inspect_core|no|degraded|New sessions fail address allocation across unrelated sites. The shared core address pool is exhausted; existing sessions remain stable.
validation|core_service_discovery|core|inspect_core|no|degraded|Core functions cannot discover session-service endpoints. The service registry health check fails while network reachability succeeds.
test|core_certificate|core|inspect_core|no|outage|Core service-to-service authentication fails after a certificate expired. Radio and transport checks pass on independent access paths.
test|core_signaling|core|inspect_core|no|degraded|A shared core signaling worker queue is stalled. Requests from independent access paths reach it but are not processed.
train|noc_missing|noc|gather_evidence|yes|unknown|Only an unreachable-site alarm is available. Power telemetry and the relevant transport dependency map are missing.
train|noc_stale|noc|gather_evidence|yes|unknown|The only transport fault record is 75 minutes old. No current power, radio, or transport observations are available.
train|noc_conflict|noc|gather_evidence|yes|unknown|Two current probes disagree about site reachability. Neither probe has an independent health check, so the observations cannot yet be reconciled.
train|noc_change|noc|verify_change|yes|degraded|Symptoms began after a configuration change. Current observations do not distinguish the changed component from an independent fault; timing alone is the only link.
train|noc_maintenance|noc|monitor|no|none|Alarms exactly match the approved maintenance assets and window. Current independent service checks show no unplanned impact. Continue observation during the work.
train|noc_recovered|noc|monitor|no|none|The alarm has cleared and independent service probes and KPIs have remained at baseline for the required observation interval. No active fault evidence remains.
validation|noc_scope|noc|verify_change|yes|degraded|Alarms extend beyond the assets in the maintenance record. The available observations do not establish which component caused the additional impact.
validation|noc_clock|noc|gather_evidence|yes|unknown|Alarm timestamps disagree because source clock offsets are unknown. Current service impact and dependencies have not been independently checked.
test|noc_nearby|noc|gather_evidence|yes|unknown|Nearby sites report similar symptoms but have independent documented transport and power paths. No current domain-specific fault evidence is available.
test|noc_clear_only|noc|gather_evidence|yes|unknown|The alarm cleared, but post-clear service measurements have not arrived. Recovery cannot yet be established from the available evidence.
validation|noc_probe_recovery|noc|monitor|no|none|Independent active probes and service KPIs confirm sustained recovery for the required observation interval after an intermittent failure. The historical alarm remains in the ticket but is not active.
test|noc_postmaintenance|noc|monitor|no|none|Planned work has ended. Independent service checks confirm sustained baseline performance for the full recovery observation interval; a delayed maintenance alarm is historical, not a current fault.'''


def scenarios():
    result = []
    for line in CATALOG.splitlines():
        split, family, owner, check, uncertain, status, evidence = line.split('|')
        result.append(dict(split=split, family=family, owner=owner, check=check,
                           uncertain=uncertain == 'yes', status=status, evidence=evidence))
    return result
