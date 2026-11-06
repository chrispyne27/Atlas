"""Explicit mappings from recorded POSIX include roots to local directories."""
from pathlib import Path, PurePosixPath


class ExternalRoots:
    def __init__(self, mappings=()):
        if len(mappings) > 16:
            raise ValueError('At most 16 external roots may be selected')
        self.roots = {}
        for prefix, directory in mappings:
            if not isinstance(prefix, str) or not 1 < len(prefix) <= 2048:
                raise ValueError('External root prefix must be an explicit absolute POSIX directory')
            key = PurePosixPath(prefix)
            if not key.is_absolute() or '..' in key.parts or str(key) != prefix.rstrip('/') or str(key) == '/':
                raise ValueError('External root prefix must be normalized, absolute and narrower than /')
            if key in self.roots:
                raise ValueError('Duplicate external root prefix')
            root = Path(directory).resolve(strict=True)
            if not root.is_dir() or root == Path(root.anchor):
                raise ValueError('External local root must be a directory narrower than filesystem root')
            self.roots[key] = root

    def locate(self, artifact):
        # No filesystem operation on the recorded absolute path itself.
        text = artifact[len('external:'):]
        key = PurePosixPath(text)
        if not key.is_absolute() or '..' in key.parts or str(key) != text:
            return None
        for prefix in sorted(self.roots, key=lambda value: len(value.parts), reverse=True):
            if key.is_relative_to(prefix):
                base = self.roots[prefix]
                return base / key.relative_to(prefix), base
        return None

    def describe(self):
        return [{'recorded_prefix': str(key), 'local_root': str(value)}
                for key, value in sorted(self.roots.items(), key=lambda item: str(item[0]))]


def mapping_argument(value):
    prefix, separator, directory = value.partition('=')
    if not separator or not prefix or not directory:
        raise ValueError('Use RECORDED_PREFIX=LOCAL_DIRECTORY for an external root')
    return prefix, directory
