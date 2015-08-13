
import os
import re
import logging
from datetime import timedelta

import yaml
from six import integer_types

from .filematch import match_key


logger = logging.getLogger(__name__)


def load_config_file(path):
    """Load configuration settings from file.

    Return tuple of configuration dictionary and base path.
    """
    if os.path.isdir(path):
        for filename in ('.s3_website.yaml', '.s3_website.yml'):
            filepath = os.path.join(path, filename)
            try:
                with open(filepath, 'r') as f:
                    config = yaml.safe_load(f)
            except:
                logger.debug('Unable to load config from {}'.format(filepath),
                             exc_info=True)
            else:
                base_path = path
                break
        else:
            raise ValueError(
                'Unable to find .s3_website.yaml in {}'.format(path))
    else:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
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
        if match_key(rule['match'], key_name):
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
                    cache_control = 'maxage={}'.format(maxage)
                else:
                    cache_control += ', maxage={}'.format(maxage)
            return cache_control

    return None
