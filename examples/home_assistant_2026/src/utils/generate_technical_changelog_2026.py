#!/usr/bin/env python3
import re
from collections import OrderedDict

RAW = '/mnt/bunker_data/ai/data_factory/data/raw/raw_changelog.txt'
OUT = '/mnt/bunker_data/ai/data_factory/data/raw/technical_changelog_2026.md'

version_re = re.compile(r'^(\d{4}\.\d+(?:\.\d+)*(?:b\d+)?)\b')
change_re = re.compile(r'^(?:[>\s\-\*]*)?(Fix|Add|Update|Bump|Remove)\b', re.I)

def clean_change(line):
    s = re.sub(r'^[>\s\-\*]+', '', line)
    # remove parentheses that contain @ or # (contributors/PRs)
    s = re.sub(r'\([^)]*[@#][^)]*\)', '', s)
    # remove any leftover (breaking...) tokens
    s = re.sub(r'\([^)]*breaking[^)]*\)', '', s, flags=re.I)
    # remove @user and #12345 anywhere
    s = re.sub(r'@\S+', '', s)
    s = re.sub(r'#\d+', '', s)
    # remove empty parentheses
    s = re.sub(r'\(\s*\)', '', s)
    # collapse spaces
    s = re.sub(r'\s+', ' ', s).strip()
    # strip leading/trailing separators
    s = s.strip(' -–—')
    return s

def include_version(ver: str) -> bool:
    """Return True if version string falls between 2024.7 and 2026.2 inclusive."""
    m = re.match(r'^(\d{4})\.(\d+)', ver)
    if not m:
        return False
    year = int(m.group(1))
    month = int(m.group(2))
    # lower bound: 2024.7 (July 2024)
    if (year, month) < (2024, 7):
        return False
    # upper bound: 2026.2 (Feb 2026)
    if (year, month) > (2026, 2):
        return False
    return True
def main():
    versions = OrderedDict()
    current_version = None
    include_block = False
    skip_section = False

    with open(RAW, 'r', encoding='utf-8', errors='ignore') as f:
        for raw_line in f:
            line = raw_line.rstrip('\n')
            m = version_re.match(line.strip())
            if m:
                current_version = m.group(1)
                include_block = include_version(current_version)
                skip_section = False
                if include_block and current_version not in versions:
                    versions[current_version] = {'changes': [], 'breaking': []}
                continue

            if not include_block or current_version is None:
                continue

            stripped = line.strip()
            low = stripped.lower()
            # skip Contributors, Assets and reaction lines (and their following blobs)
            if low.startswith('contributors') or low.startswith('assets') or 'reacted' in low or re.match(r'^\d+\s+people reacted', low):
                skip_section = True
                continue
            if skip_section:
                continue

            t = re.sub(r'^[>\s\-\*]+', '', line)
            if not t:
                continue
            m2 = change_re.match(t)
            if not m2:
                continue

            is_breaking = 'breaking' in line.lower()
            cleaned = clean_change(t)
            if not cleaned:
                continue
            if is_breaking:
                versions[current_version]['breaking'].append(cleaned)
            else:
                versions[current_version]['changes'].append(cleaned)

    # write output
    out_lines = []
    for ver, data in versions.items():
        if not data['changes'] and not data['breaking']:
            continue
        out_lines.append(f'## {ver}')
        out_lines.append('')
        if data['changes']:
            for c in data['changes']:
                out_lines.append(f'- {c}')
            out_lines.append('')
        if data['breaking']:
            out_lines.append('### BREAKING CHANGES')
            out_lines.append('')
            for b in data['breaking']:
                out_lines.append(f'- {b}')
            out_lines.append('')

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))

    print('Wrote', OUT)

if __name__ == '__main__':
    main()
