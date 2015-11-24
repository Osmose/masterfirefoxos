from django.conf import settings

from masterfirefoxos.base.utils import (
    execute,
    po_filename,
    po_filenames_for_locale,
)


def run(*args):
    """
    Collect the individual pofiles for each locale into a single
    django.po file for Django to compile. Uses the msgcat command from
    gettext to combine the pofiles together.
    """
    for locale, lang_name in settings.LANGUAGES:
        po_filenames = po_filenames_for_locale(locale)
        output_filename = po_filename(locale, 'django')

        command = ['msgcat'] + po_filenames + ['-o', output_filename, '--use-first']
        code, output, error = execute(command)
        if code != 0:
            print('Cannot collect strings for locale {}: {}'.format(locale, error))
