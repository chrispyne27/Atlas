"""Bounded, nonrecursive discovery for the explicit F Prime engineering adapter."""
import os
from pathlib import Path

VERSION = 'fprime-engineering-membership-1'
COMPONENTS = {'Svc/Health', 'Svc/CmdDispatcher'}
MAX_ENTRIES = 1000


def capture(repository, component):
    if component not in COMPONENTS:
        raise ValueError('Unsupported engineering component')
    root = Path(repository).resolve(strict=True)
    result = {'version': VERSION, 'component': component, 'directories': []}
    for relative, suffix in [(component + '/docs', '.md'), (component + '/test/ut', '.cpp')]:
        folder = (root / relative).resolve(strict=True)
        if not folder.is_relative_to(root):
            raise ValueError('Discovery directory escaped repository')
        members = []
        with os.scandir(folder) as entries:
            for count, entry in enumerate(entries, 1):
                if count > MAX_ENTRIES:
                    raise ValueError('Discovery directory entry budget exceeded')
                if not entry.name.endswith(suffix):
                    continue
                target = Path(entry.path).resolve(strict=True)
                if not target.is_relative_to(root):
                    raise ValueError('Discovery member escaped repository')
                if not target.is_file():
                    raise ValueError('Discovery member is not a regular file')
                member = {'path': relative + '/' + entry.name,
                          'resolved_path': target.relative_to(root).as_posix()}
                if any(len(value) > 2048 for value in member.values()):
                    raise ValueError('Discovery member path exceeds budget')
                members.append(member)
        result['directories'].append({'path': relative, 'suffix': suffix,
                                      'members': sorted(members, key=lambda item: item['path'])})
    return result


def compare(repository, component, recorded):
    if not isinstance(recorded, dict) or recorded.get('version') != VERSION:
        return {'component': component, 'status': 'not_recorded'}
    if repository is None:
        return {'component': component, 'status': 'root_not_supplied'}
    try:
        current = capture(repository, component)
    except FileNotFoundError:
        return {'component': component, 'status': 'missing_directory_or_member'}
    except (OSError, RuntimeError, ValueError):
        return {'component': component, 'status': 'unavailable'}
    # Includes policy, component, directory and resolved symlink identities.
    if current == recorded:
        return {'component': component, 'status': 'matched'}
    return {'component': component, 'status': 'changed'}
