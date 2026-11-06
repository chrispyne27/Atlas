"""Request-scoped detail assembly under the trace transaction and budgets."""
from .store import canonical
from .details import DETAIL_BYTES

# Fixed defaults/maxima; per-call DetailInspector caps also remain in force.
DETAIL_LIMITS = dict(evidence_calls=50, evidence_items=50, evidence_bytes=256*1024,
                     occurrence_items=50, source_calls=20, source_files=8,
                     source_bytes=32*1024*1024, source_hash_bytes=32*1024*1024)


def assemble(reader, packet, query, roots, measure, reserve):
    usage = packet['usage']
    limits = packet['limits']
    max_bytes = limits['max_bytes']

    def omit(reason):
        if reason not in packet['omissions']:
            packet['omissions'].append(reason)

    def fits():
        return measure(packet)+reserve <= max_bytes

    # At most one occurrence per entity, with a bounded lookahead for alternatives.
    for entity in packet['entities']:
        entity['source_status'] = 'no_selected_occurrence'
        entity['occurrence_selection'] = 'one selected target/shared occurrence; other variants may be omitted'
        if usage['occurrence_items'] >= limits['occurrence_items']:
            entity['source_status'] = 'budget_omitted'
            omit('occurrence_item_limit')
            continue
        rows = query('''SELECT o.id,o.entity_id,o.compilation_id,
            substr(o.artifact_path,1,2048) AS artifact_path,o.start_line,o.end_line,o.role,o.evidence_id,
            length(o.artifact_path)>2048 AS fields_truncated
            FROM occurrence o LEFT JOIN compilation c ON c.snapshot_id=o.snapshot_id AND c.id=o.compilation_id
            WHERE o.snapshot_id=? AND o.entity_id=? AND (o.compilation_id IS NULL OR c.target_id=?)
            ORDER BY CASE WHEN o.role='definition' THEN 0 ELSE 1 END,o.compilation_id,o.id LIMIT 2''',
            (packet['snapshot']['id'], entity['id'], packet['target'])).fetchall()
        usage['occurrence_rows'] += len(rows)
        if not rows:
            continue
        occurrence = dict(rows[0])
        occurrence['other_variants_observed'] = len(rows) > 1
        occurrence['applicability'] = ('snapshot-shared; target applicability unverified'
            if occurrence['compilation_id'] is None else 'selected target compilation')
        occurrence['evidence_details_status'] = 'budget_omitted'
        occurrence['source'] = dict(status='budget_omitted', text=None)
        packet['occurrences'].append(occurrence)
        if not fits():
            packet['occurrences'].pop()
            entity['source_status'] = 'budget_omitted'
            omit('occurrence_byte_limit')
            continue
        usage['occurrence_items'] += 1
        if usage['source_calls'] >= limits['source_calls']:
            omit('source_call_limit')
        else:
            usage['source_calls'] += 1
            # Source identity comes from this occurrence, never from a different
            # evidence span or a preferred body in another compilation.
            item = dict(id=occurrence['evidence_id'], artifact_path=occurrence['artifact_path'],
                        fields_truncated=occurrence['fields_truncated'], line=occurrence['start_line'])
            start = occurrence['start_line']
            end = min(occurrence['end_line'], start+199)
            result = reader._source_item(packet['snapshot'], packet['target'], item, roots,
                start, end, query=query, budget=(limits, usage))
            result['span_truncated'] = end < occurrence['end_line']
            if result['status'] == 'unavailable':
                reason = result.get('reason', '')
                result['status'] = ('external_unavailable' if item['artifact_path'].startswith('external:') else
                    'root_unavailable' if 'root not explicitly' in reason else
                    'missing' if 'missing or unreadable' in reason or 'artifact absent' in reason else 'unavailable')
            occurrence['source'] = result
            if not fits():
                result = dict(status='budget_omitted', text=None,
                    expected_hash=result.get('expected_hash'), start_line=start, end_line=end,
                    span_truncated=end < occurrence['end_line'])
                occurrence['source'] = result
                omit('source_byte_limit')
            if result['status'] == 'budget_omitted':
                omit('source_budget_omitted')
        entity['source_status'] = occurrence['source']['status']

    references = packet['relationships']+packet['occurrences']
    evidence_status = {}
    for reference in references:
        eid = reference['evidence_id']
        if eid not in evidence_status:
            status = 'budget_omitted'
            if usage['evidence_calls'] < limits['evidence_calls']:
                usage['evidence_calls'] += 1
                detail = reader._evidence(packet['snapshot']['id'], packet['target'], eid, query=query)
                if len(canonical(detail).encode('utf-8')) > DETAIL_BYTES:
                    detail['details'] = None
                    detail['details_status'] = 'over_limit'
                cost = len(canonical(detail).encode('utf-8'))
                if usage['evidence_bytes']+cost <= limits['evidence_bytes']:
                    usage['evidence_bytes'] += cost
                    packet['evidence'].append(detail)
                    if fits():
                        status = detail['details_status']
                        usage['evidence_items'] += 1
                    else:
                        packet['evidence'].pop()
                        omit('evidence_byte_limit')
                else:
                    # Charge bounded work even when the body cannot be delivered.
                    omit('evidence_aggregate_byte_limit')
            if status == 'budget_omitted':
                omit('evidence_details_omitted')
            evidence_status[eid] = status
        reference['evidence_details_status'] = evidence_status[eid]
    packet['evidence_details_status'] = 'bounded_selected_details; omissions labeled on references'
