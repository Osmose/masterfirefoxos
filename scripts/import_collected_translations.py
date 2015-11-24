from django.conf import settings

import polib

from masterfirefoxos.base.utils import (
    po_filename,
    po_filenames_for_locale,
)


def run(*args):
    """
    One-time script to import translations from django.po files to the separated
    Firefox OS and messages.po files.
    """
    for locale, lang_name in settings.LANGUAGES:
        collected_po_filename = po_filename(locale, 'django')
        try:
            collected_po = polib.pofile(collected_po_filename)
        except (IOError, OSError) as err:
            print('Cannot open po file {}: {}'.format(collected_po_filename, err))
            continue

        for filename in po_filenames_for_locale(locale):
            try:
                po = polib.pofile(filename)
            except (IOError, OSError) as err:
                print('Cannot open po file {}: {}'.format(po_filename, err))
                continue

            for entity in po:
                collected_entity = collected_po.find(entity.msgid)
                if collected_entity is not None and collected_entity.msgstr:
                    entity.msgstr = collected_entity.msgstr

            po.save()
