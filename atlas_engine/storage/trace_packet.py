"""Bounded inspection trace packets; never freshness-eligible agent context."""
from collections import deque
import argparse
import sqlite3
import time
from .details import DetailInspector
from .trace_details import DETAIL_LIMITS, assemble
from .store import canonical

RELATION_KINDS = ('calls', 'test_body', 'invokes_annotated_helper',
                  'has_requirement_annotation', 'annotates_requirement', 'candidate_alias')
# Aggregate traversal limits; DETAIL_LIMITS overlays the source/detail caps.
WORK_LIMITS = dict(sql_statements=500, rows=1000, adjacency_rows=200,
                   query_vm_steps=2000000, sql_seconds=0.5, source_files=0,
                   source_bytes=0, source_hash_bytes=0)


class PacketBudgetError(ValueError):
    def __init__(self):
        self.response = {'error': 'packet_budget_too_small', 'inspection_only': True,
                         'context_eligible': False}
        super().__init__('Seed and required envelope exceed packet byte budget')


def _measure(packet):
    # Include the decimal byte count itself in the compact UTF-8 delivery size.
    while True:
        size = len(canonical(packet).encode('utf-8'))
        if packet['usage']['bytes'] == size:
            return size
        packet['usage']['bytes'] = size


class TracePacketInspector(DetailInspector):
    def packet(self, *, snapshot, target, entity, direction='out', kinds=None,
               max_depth=3, max_nodes=50, max_edges=100, max_bytes=64*1024, roots=None):
        if not all(isinstance(x, str) and 0 < len(x) <= 2048
                   for x in (snapshot, target, entity)):
            raise ValueError('Invalid snapshot, target or exact entity ID')
        if direction not in ('out', 'in', 'both'):
            raise ValueError('Invalid direction')
        for name, value, minimum, maximum in (
                ('max_depth', max_depth, 0, 3), ('max_nodes', max_nodes, 1, 200),
                ('max_edges', max_edges, 1, 500), ('max_bytes', max_bytes, 1, 256*1024)):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError('Invalid '+name)
        if kinds is None:
            kinds = RELATION_KINDS
        if (not isinstance(kinds, (tuple, list)) or not kinds or
                any(not isinstance(k, str) or k not in RELATION_KINDS for k in kinds)):
            raise ValueError('Unsupported relationship kinds')
        kinds = sorted(set(kinds))
        roots = {} if roots is None else roots
        if not isinstance(roots, dict) or any(k not in ('repo', 'build') for k in roots):
            raise ValueError('Unsupported source roots')
        version = self._version()
        deadline = time.monotonic()+WORK_LIMITS['sql_seconds']
        ticks = 0
        usage = dict(sql_statements=0, rows=0, bytes=0, source_files=0,
                     source_bytes=0, source_hash_bytes=0)

        usage.update(evidence_calls=0, evidence_items=0, evidence_bytes=0, occurrence_items=0,
                     occurrence_rows=0, source_calls=0)

        def stop():
            nonlocal ticks
            ticks += 1
            return ticks >= WORK_LIMITS['query_vm_steps']//1000 or time.monotonic() > deadline

        def query(sql, params):
            if usage['sql_statements'] >= WORK_LIMITS['sql_statements']:
                raise ValueError('Aggregate SQL statement budget exceeded')
            usage['sql_statements'] += 1
            return self.db.execute(sql, params)

        def node(eid):
            row = query('''SELECT id,kind,substr(scope,1,2048) AS scope,
                substr(external_key,1,2048) AS external_key,substr(name,1,2048) AS name,
                (length(scope)>2048 OR length(external_key)>2048 OR length(name)>2048) AS fields_truncated
                FROM entity WHERE snapshot_id=? AND id=?''', (snapshot, eid)).fetchone()
            if row is None:
                raise ValueError('Missing relation endpoint')
            result = dict(row)
            result['source_status'] = 'no_selected_occurrence'
            result['occurrence_selection'] = 'one selected target/shared occurrence; other variants may be omitted'
            return result

        self.db.set_progress_handler(stop, 1000)
        self.db.execute('BEGIN')
        try:
            snap = query('SELECT id,revision,configuration_key,state,input_manifest_hash FROM snapshot WHERE id=?', (snapshot,)).fetchone()
            if snap is None or not query('SELECT 1 FROM build_target WHERE snapshot_id=? AND id=?', (snapshot, target)).fetchone():
                raise ValueError('Unknown snapshot or target')
            params = dict(snapshot=snapshot, target=target, entity=entity)
            if not query(f'''SELECT 1 FROM entity e WHERE e.snapshot_id=:snapshot
                    AND e.id=:entity AND {self._visibility('e')}''', params).fetchone():
                raise ValueError('Entity is absent from selected target/shared scope')
            seed = node(entity)
            seed['inclusion'] = {'reason': 'exact_seed', 'depth': 0, 'via_relation': None}
            packet = dict(packet_schema_version=1, inspection_only=True, context_eligible=False,
                snapshot=dict(snap), target=target, seed=entity,
                scope='partial snapshot inspection; shared evidence target applicability unverified',
                freshness='whole-graph freshness not established',
                request=dict(direction=direction, kinds=kinds),
                limits=dict(max_depth=max_depth, max_nodes=max_nodes, max_edges=max_edges,
                            max_bytes=max_bytes, **dict(WORK_LIMITS, **DETAIL_LIMITS)), usage=usage,
                entities=[seed], relationships=[], occurrences=[], evidence=[], omissions=[],
                counts_scope='returned packet and bounded adjacency observations only; no exhaustive counts',
                unresolved_returned=0, candidates_returned=0, resumable=False,
                evidence_details_status='not_assembled_in_core')
            # Reserve enough for every fixed omission reason and final counters.
            reserve = 2048
            if _measure(packet)+reserve > max_bytes:
                raise PacketBudgetError()
            seen_nodes = {entity}
            seen_edges = set()
            scheduled = {entity}
            queue = deque([(entity, 0)])

            def omit(reason):
                if reason not in packet['omissions']:
                    packet['omissions'].append(reason)

            while queue:
                current, depth = queue.popleft()
                if depth >= max_depth:
                    omit('depth_limit; boundary adjacency not inspected')
                    continue
                for orientation in (('out', 'in') if direction == 'both' else (direction,)):
                    remaining = WORK_LIMITS['rows']-usage['rows']
                    if remaining <= 0:
                        omit('aggregate_row_limit; remaining adjacency not inspected')
                        queue.clear()
                        break
                    column = 'from_entity' if orientation == 'out' else 'to_entity'
                    rows = query(f'''SELECT r.id,r.from_entity,r.to_entity,r.kind,r.resolution,
                        r.compilation_id,r.evidence_id,substr(r.target_spelling,1,2048) AS target_spelling,
                        e.kind AS provenance,substr(e.artifact_path,1,2048) AS artifact_path,
                        e.line,substr(e.producer,1,2048) AS producer,
                        (length(coalesce(r.target_spelling,''))>2048 OR length(coalesce(e.artifact_path,''))>2048 OR length(e.producer)>2048) AS fields_truncated,
                        CASE WHEN r.compilation_id IS NULL THEN 'snapshot-shared; target applicability unverified'
                             ELSE 'selected target compilation' END AS applicability
                        FROM relation r JOIN evidence e ON e.snapshot_id=r.snapshot_id AND e.id=r.evidence_id
                        LEFT JOIN compilation c ON c.snapshot_id=r.snapshot_id AND c.id=r.compilation_id
                        WHERE r.snapshot_id=? AND r.{column}=?
                        AND (r.compilation_id IS NULL OR c.target_id=?)
                        ORDER BY r.kind,r.id LIMIT ?''',
                        (snapshot, current, target, min(remaining, WORK_LIMITS['adjacency_rows']+1)))
                    for index, row in enumerate(rows):
                        usage['rows'] += 1
                        if index == WORK_LIMITS['adjacency_rows']:
                            omit('adjacency_row_limit; further rows not inspected')
                            break
                        edge = dict(row)
                        if edge['kind'] not in kinds:
                            omit('relationship_kind_filtered; observed rows only')
                            continue
                        if edge['id'] in seen_edges:
                            continue
                        if len(seen_edges) >= max_edges:
                            omit('edge_limit; remaining adjacency not inspected')
                            queue.clear()
                            break
                        endpoint = edge['to_entity'] if orientation == 'out' else edge['from_entity']
                        added = None
                        if endpoint is not None and endpoint not in seen_nodes:
                            if len(seen_nodes) >= max_nodes:
                                omit('node_limit; relation and endpoint omitted together')
                                continue
                            added = node(endpoint)
                            added['inclusion'] = dict(reason=edge['resolution']+'_endpoint',
                                depth=depth+1, via_relation=edge['id'], from_entity=current)
                        edge['evidence_details_status'] = 'budget_omitted'
                        edge['inclusion'] = dict(from_entity=current, direction=orientation, depth=depth+1)
                        edge['traversal'] = 'resolved_endpoint_eligible' if edge['resolution'] == 'resolved' else 'terminal'
                        packet['relationships'].append(edge)
                        if added is not None:
                            packet['entities'].append(added)
                        if _measure(packet)+reserve > max_bytes:
                            packet['relationships'].pop()
                            if added is not None:
                                packet['entities'].pop()
                            omit('byte_limit; relation and endpoint omitted together')
                            queue.clear()
                            break
                        seen_edges.add(edge['id'])
                        if added is not None:
                            seen_nodes.add(endpoint)
                        if edge['resolution'] == 'resolved' and endpoint not in scheduled:
                            scheduled.add(endpoint)
                            queue.append((endpoint, depth+1))
                        if edge['resolution'] == 'candidate':
                            omit('candidate_links_terminal')
            packet['unresolved_returned'] = sum(e['resolution'] == 'unresolved' for e in packet['relationships'])
            packet['candidates_returned'] = sum(e['resolution'] == 'candidate' for e in packet['relationships'])
            assemble(self, packet, query, roots, _measure, reserve)
            packet['omissions'].sort()
            if _measure(packet) > max_bytes:
                raise PacketBudgetError()
            self.db.execute('COMMIT')
            if self._version() != version:
                raise ValueError('Database changed during inspection; retry')
            return packet
        except sqlite3.OperationalError as error:
            if 'interrupted' in str(error):
                raise ValueError('Aggregate SQL work/time budget exceeded; packet rejected') from error
            raise
        finally:
            self.db.set_progress_handler(None, 0)
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('database', 'snapshot', 'target', 'entity'):
        parser.add_argument('--'+key, required=True)
    parser.add_argument('--direction', choices=('out', 'in', 'both'), default='out')
    parser.add_argument('--kind', action='append', dest='kinds', choices=RELATION_KINDS)
    for key, default in (('max_depth', 3), ('max_nodes', 50), ('max_edges', 100), ('max_bytes', 64*1024)):
        parser.add_argument('--'+key.replace('_', '-'), type=int, default=default)
    parser.add_argument('--repo-root');parser.add_argument('--build-root')
    args = vars(parser.parse_args(argv))
    roots = {key: args.pop(key+'_root') for key in ('repo', 'build')}
    args['roots'] = {key: value for key, value in roots.items() if value is not None}
    reader = None
    try:
        reader = TracePacketInspector(args.pop('database'))
        print(canonical(reader.packet(**args)))
        return 0
    except (ValueError, OSError, sqlite3.Error) as error:
        result = error.response if isinstance(error, PacketBudgetError) else dict(
            error='inspection_failed', message=str(error), inspection_only=True, context_eligible=False)
        print(canonical(result))
        return 2
    finally:
        if reader is not None:
            reader.close()


if __name__ == '__main__':
    raise SystemExit(main())
