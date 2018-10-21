
import os
import re
import logging
from datetime import timedelta

import yaml
from six import integer_types

from .filematch import match_key


logger = logging.getLogger(__name__)


def _load_config_from_path(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def load_config_file(path):
    """Load configuration settings from file.

    Return tuple of configuration dictionary and base path.
    """
    if os.path.isdir(path):
        for filename in ('.s3_website.yaml', '.s3_website.yml'):
            filepath = os.path.join(path, filename)
            try:
                config = _load_config_from_path(filepath)
            except Exception:
                logger.debug('Unable to load config from {}'.format(filepath),
                             exc_info=True)
            else:
                base_path = path
                break
        else:
            raise ValueError(
                'Unable to find .s3_website.yaml in {}'.format(path))
    else:
        config = _load_config_from_path(path)
        base_path = os.path.dirname(path)

    return config, base_path


def timedelta_from_duration_string(s):
    """Convert time duration string to number of seconds."""
    if re.match(r'^\d+$', s):
        return timedelta(seconds=int(s))

    td_args = {}
    for part in s.split(','):
        part = part.strip()
        m = re.match(r'(\d+)\s+(year|month|day|hour|minute|second)s?', part)
        if not m:
            raise ValueError(
                'Unable to parse duration string: {}'.format(part))

        if m.group(2) == 'month':
            td_args['days'] = int(m.group(1)) * 30
        elif m.group(2) == 'year':
            td_args['days'] = int(m.group(1)) * 365
        else:
            td_args[m.group(2) + 's'] = int(m.group(1))

    return timedelta(**td_args)


def resolve_cache_rules(key_name, rules):
    """Returns the value of the Cache-Control header after applying rules."""

    for rule in rules:
        has_match = 'match' in rule
        has_match_regexp = 'match_regexp' in rule
        if has_match == has_match_regexp:
            raise ValueError(
                'Cache rule must have either match or match_regexp key'
            )

        pattern = rule['match'] if has_match else rule['match_regexp']

        if match_key(pattern, key_name, regexp=has_match_regexp):
            cache_control = None
            if 'cache_control' in rule:
                cache_control = rule['cache_control']
            if 'maxage' in rule:
                if isinstance(rule['maxage'], integer_types):
                    maxage = rule['maxage']
                else:
                    td = timedelta_from_duration_string(rule['maxage'])
                    maxage = int(td.total_seconds())
                if cache_control is None:
                    cache_control = 'max-age={}'.format(maxage)
                else:
                    cache_control += ', max-age={}'.format(maxage)
            return cache_control

    return None
