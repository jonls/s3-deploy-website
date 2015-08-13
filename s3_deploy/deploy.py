
import os
import re
import argparse
import logging
import gzip
import shutil
from email.utils import parsedate_tz, mktime_tz
import mimetypes

import boto
from boto.s3.connection import S3Connection, OrdinaryCallingFormat
from boto.s3.key import Key

from six import BytesIO

from . import config
from .prefixcovertree import PrefixCoverTree


COMPRESSED_EXTENSIONS = frozenset([
    '.txt', '.html', '.css', '.js', '.json', '.xml', '.rss'])

logger = logging.getLogger(__name__)

mimetypes.init()


def key_name_from_path(path):
    """Convert a relative path into a key name."""
    key_parts = []
    while True:
        head, tail = os.path.split(path)
        if tail != '.':
            key_parts.append(tail)
        if head == '':
            break
        path = head

    return '/'.join(reversed(key_parts))


def upload_key(key, path, cache_rules, dry, replace=False):
    """Upload data in path to key."""

    mime_guess = mimetypes.guess_type(key.key)
    if mime_guess is not None:
        content_type = mime_guess[0]
    else:
        content_type = 'application/octet-stream'

    content_file = open(path, 'rb')
    try:
        encoding = None

        cache_control = config.resolve_cache_rules(key.key, cache_rules)
        if cache_control is not None:
            logger.debug('Using cache control: {}'.format(cache_control))

        _, ext = os.path.splitext(path)
        if ext in COMPRESSED_EXTENSIONS:
            logger.info('Compressing {}...'.format(key.key))
            compressed = BytesIO()
            gzip_file = gzip.GzipFile(
                fileobj=compressed, mode='wb', compresslevel=9)
            try:
                shutil.copyfileobj(content_file, gzip_file)
            finally:
                gzip_file.close()
            compressed.seek(0)
            content_file, _ = compressed, content_file.close()  # noqa
            encoding = 'gzip'

        logger.info('Uploading {}...'.format(key.key))

        if not dry:
            if content_type is not None:
                key.set_metadata('Content-Type', content_type)
            if cache_control is not None:
                key.set_metadata(
                    'Cache-Control', cache_control.encode('ascii'))

            if encoding is not None:
                key.set_metadata('Content-Encoding', encoding)

            key.set_contents_from_file(content_file, replace=replace)
    finally:
        content_file.close()


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='AWS S3 website deployment tool')
    parser.add_argument(
        '-f', '--force', action='store_true', dest='force',
        help='force upload of all files')
    parser.add_argument(
        '-n', '--dry-run', action='store_true', dest='dry',
        help='run without uploading any files')
    parser.add_argument(
        'path', help='the .s3_website.yaml configuration file or directory',
        default='.', nargs='?')
    args = parser.parse_args()

    # Open configuration file
    conf, base_path = config.load_config_file(args.path)

    bucket_name = conf['s3_bucket']
    cache_rules = conf.get('cache_rules', [])

    logger.info('Connecting to bucket {}...'.format(bucket_name))

    conn = S3Connection(calling_format=OrdinaryCallingFormat())
    bucket = conn.get_bucket(bucket_name, validate=False)

    site_dir = os.path.join(base_path, conf['site'])

    logger.info('Site: {}'.format(site_dir))

    processed_keys = set()
    updated_keys = set()

    for key in bucket:
        processed_keys.add(key.key)
        path = os.path.join(site_dir, key.key)

        # Delete keys that have been deleted locally
        if not os.path.isfile(path):
            logger.info('Deleting {}...'.format(key.key))
            if not args.dry:
                key.delete()
            updated_keys.add(key.key)
            continue

        # Skip keys that have not been updated
        mtime = int(os.path.getmtime(path))
        if not args.force:
            # Update key metadata if not available.
            # The bucket list() call that is executed through the bucket
            # iteration above actually does obtain the last modified date
            # from the server, but boto currently does not update the key
            # variables based on that. We need to do an additional get_key()
            # request to get the field populated.
            key = bucket.get_key(key.key)
            key_mtime = mktime_tz(parsedate_tz(key.last_modified))
            if mtime <= key_mtime:
                logger.info('Not modified, skipping {}.'.format(key.key))
                continue

        upload_key(key, path, cache_rules, args.dry, replace=True)
        updated_keys.add(key.key)

    for dirpath, dirnames, filenames in os.walk(site_dir):
        key_base = os.path.relpath(dirpath, site_dir)
        for name in filenames:
            path = os.path.join(dirpath, name)
            key_name = key_name_from_path(os.path.join(key_base, name))
            if key_name in processed_keys:
                continue

            # Create new key
            key = Key(bucket)
            key.key = key_name

            logger.info('Creating key {}...'.format(key_name))

            upload_key(key, path, cache_rules, args.dry, replace=False)
            updated_keys.add(key_name)

    logger.info('Bucket update done.')

    # Invalidate files in cloudfront distribution
    if 'cloudfront_distribution_id' in conf:
        logger.info('Connecting to Cloudfront distribution {}...'.format(
            conf['cloudfront_distribution_id']))

        index_pattern = None
        if 'index_document' in conf:
            index_doc = conf['index_document']
            index_pattern = r'(^(?:.*/)?)' + re.escape(index_doc) + '$'

        def path_from_key_name(key_name):
            if index_pattern is not None:
                m = re.match(index_pattern, key_name)
                if m:
                    return m.group(1)
            return key_name

        t = PrefixCoverTree()
        for key_name in updated_keys:
            t.include(path_from_key_name(key_name))
        for key_name in processed_keys - updated_keys:
            t.exclude(path_from_key_name(key_name))

        paths = []
        for prefix, exact in t.matches():
            path = '/' + prefix + ('' if exact else '*')
            logger.info('Preparing to invalidate {}...'.format(path))
            paths.append(path)

        conn = boto.connect_cloudfront()

        if len(paths) > 0:
            dist_id = conf['cloudfront_distribution_id']
            if not args.dry:
                logger.info('Creating invalidation request...')
                conn.create_invalidation_request(dist_id, paths)
        else:
            logger.info('Nothing updated, skipping invalidation...')

        logger.info('Cloudfront invalidation done.')
