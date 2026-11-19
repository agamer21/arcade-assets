"""Prepare an asset-only Pages artifact from the pinned Gang Beasts port."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import time
import urllib.request

SOURCE = 'https://raw.githubusercontent.com/Reeyuki/GangBeast-WebPort/7016e4b49e435425173434233c6ceae6d8e34e41/'
MANIFESTS = Path(__file__).resolve().parent / 'manifests'


def read_part(name, size, source_directory):
    if source_directory is not None:
        data = (source_directory / name).read_bytes()
        if len(data) != size:
            raise ValueError(f'{name}: invalid size')
        return data

    for attempt in range(3):
        try:
            with urllib.request.urlopen(SOURCE + name, timeout=60) as response:
                data = response.read(size + 1)
            if len(data) != size:
                raise ValueError(f'{name}: expected {size} bytes, got {len(data)}')
            return data
        except (OSError, ValueError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def stage_manifest(manifest, destination, source_directory):
    def stage_part(part):
        name = part['url']
        data = read_part(name, part['size'], source_directory)
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    checksum = hashlib.sha256()
    size = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for path in pool.map(stage_part, manifest['parts']):
            with path.open('rb') as file:
                for block in iter(lambda: file.read(1024 * 1024), b''):
                    size += len(block)
                    checksum.update(block)
    if size != manifest['size'] or checksum.hexdigest() != manifest['sha256']:
        raise ValueError('Assembled size or checksum differs from the pinned port.')
    print(f'Verified {len(manifest["parts"])} parts, {size:,} bytes.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--source-directory', type=Path)
    options = parser.parse_args()
    options.destination.mkdir(parents=True, exist_ok=True)
    (options.destination / '.nojekyll').touch()
    for manifest_path in sorted(MANIFESTS.glob('*.json')):
        manifest = json.loads(manifest_path.read_text())
        stage_manifest(manifest, options.destination / 'gang-beasts', options.source_directory)
    (options.destination / 'index.html').write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>AG Arcade assets</title>'
        '<p>Game assets for <a href="/">AG Arcade</a>.</p></html>\n'
    )


if __name__ == '__main__':
    main()
