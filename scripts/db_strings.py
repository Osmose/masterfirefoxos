import os
from collections import defaultdict

from django.conf import settings

import polib
from feincms.module.page.models import Page

from masterfirefoxos.base.utils import (
    execute,
    versions_for_locale,
    page_strings,
    versions_po_filename,
)


def run(*args):
    """
    Collect strings that are stored in the database and output / update
    pofiles for them into the locale folders.

    For each locale, one pofile is generated for each Firefox OS version
    available in that locale, plus one pofile for strings that are
    shared across multiple versions.
    """
    # string_meta maps the string to a dict of the version it occurs
    # in and the urls it appears on. We key by string so that a string
    # that appears multiple times can be marked as "shared".
    string_meta = {}
    for page in Page.objects.all():
        version = page.parent.slug if page.parent else page.slug
        url = '{parent_slug}/{page_slug}/'.format(
            parent_slug=page.parent.slug if page.parent else '',
            page_slug=page.slug,
        )
        for string in set(page_strings(page)):
            if string in string_meta:
                string_meta[string]['versions'].append(version)
                string_meta[string]['urls'].append(url)
            else:
                string_meta[string] = {
                    'versions': [version],
                    'urls': [url]
                }

    # Once we've collected the strings, group them by version instead
    # of by string. An entity in this case is a tuple (string, urls).
    # Entities are keyed by a frozenset of the version they're included
    # in.
    db_entities = defaultdict(list)
    for string, data in string_meta.items():
        entity = (string, data['urls'])
        key = frozenset(data['versions'])
        db_entities[key].append(entity)

    # Create/update po templates.
    for versions, entities in db_entities.items():
        pot_filename = versions_po_filename('templates', versions, template=True)

        # Create the file if it doesn't exist, and read it in.
        try:
            with open(pot_filename, 'a+') as f:
                f.seek(0)
                po = polib.pofile(f.read())
        except (IOError, OSError) as err:
            print('Cannot open pot file {}: {}'.format(pot_filename, err))
            continue

        # Remove unnecessary strings.
        to_remove = []
        strings = [e[0] for e in entities]
        for entry in po:
            if len(entry.occurrences) == 0:
                continue

            if entry.msgid in strings:
                continue

            to_remove.append(entry)

        for entry in to_remove:
            po.remove(entry)

        # Add missing strings.
        for string, page_urls in entities:
            if po.find(string) is None:
                po.append(polib.POEntry(
                    occurrences=[(page_url, 0) for page_url in page_urls],
                    msgid=string
                ))

        po.metadata.setdefault('Content-Type', 'text/plain; charset=UTF-8')
        po.metadata.setdefault('Content-Transfer-Encoding', '8bit')
        po.save(pot_filename)

    # Merge template files into locale-specific files.
    for locale, lang_name in settings.LANGUAGES:
        locale_versions = versions_for_locale(locale)

        # Each key in db_entities corresponds to a file we created.
        for versions in db_entities.keys():
            if not locale_versions.intersection(versions):
                continue  # Locale doesn't match this file's versions.

            po_filename = versions_po_filename(locale, versions)
            pot_filename = versions_po_filename('templates', versions, template=True)

            if not os.path.isfile(po_filename):
                code, output, error = execute([
                    'msginit',
                    '--no-translator',
                    '--locale={}'.format(locale),
                    '--input={}'.format(pot_filename),
                    '--output-file={}'.format(po_filename),
                ])
                if code != 0:
                    print('Cannot create pofile for locale {}, version {}: {}'
                          .format(locale, version, error))
                    continue

            code, output, error = execute([
                'msgmerge',
                '--update',
                '--backup=off',
                po_filename,
                pot_filename,
            ])
            if code != 0:
                print('Cannot merge strings for locale {}, version {}: {}'
                      .format(locale, version, error))
