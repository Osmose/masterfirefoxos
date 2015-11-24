import os
import subprocess
from datetime import datetime
from glob import glob

from django.db.models.fields import TextField
from django.conf import settings

from feincms.module.page.models import Page


page_template_template = '''
{{% comment %}}
Translators:
    Page path: {parent_slug}/{page_slug}/
{{% endcomment %}}
{{% blocktrans trimmed %}}
{string}
{{% endblocktrans %}}
'''


def entry_strings(entry):
    return [getattr(entry, field.name) for field in entry._meta.fields
            if field.name in getattr(entry, '_l10n_fields', [])
            and getattr(entry, field.name)]


def page_strings(page):
    """Yield an iterable of all strings within the given page."""
    yield page.title

    for content_type in page._feincms_content_types:
        for entry in page.content.all_of_type(content_type):
            for entry_string in entry_strings(entry):
                yield entry_string


def versions_for_locale(locale):
    """
    Retrieve all version slugs for versions enabled in the given locale.
    """
    versions = set()
    for version, data in settings.VERSIONS_LOCALE_MAP.items():
        if (locale in data.get('locales', [])
            or locale in data.get('pending_locales', [])):
            versions.add(data['slug'])
    return versions


def all_versions():
    """Retrieve all version slugs from settings.VERSIONS_LOCALE_MAP."""
    for data in settings.VERSIONS_LOCALE_MAP.values():
        yield data['slug']


def versions_po_filename(locale, versions, template=False):
    """
    Generate the filename of the pofile containing strings for the given
    locale and Firefox OS versions.
    """
    domain = 'firefox_os_' + '_'.join(sorted(versions))
    return po_filename(locale, domain, template=template)


def po_filename(locale, domain, template=False):
    """
    Return the filename of the pofile for the the given domain/locale.
    """
    ext = 'pot' if template else 'po'
    filename = '{domain}.{ext}'.format(domain=domain, ext=ext)

    return os.path.join(locale_dir(locale), 'LC_MESSAGES', filename)


def locale_dir(locale):
    if '-' in locale:
        lang, country = locale.split('-')
        locale = '_'.join([lang, country.upper()])
    return os.path.join(settings.BASE_DIR, 'locale', locale)


def po_filenames_for_locale(locale):
    """
    Return the filenames for all pofiles found within the given locale's
    directory.
    """
    filenames = glob(os.path.join(locale_dir(locale), '**', '*.po'))
    return [filename for filename in filenames if not filename.endswith('django.po')]


def execute(command):
    """
    Execute the given command in a subprocess synchronously. Returns a
    tuple of the form (return_code, stdout, stderr).
    """
    try:
        st = subprocess.PIPE
        proc = subprocess.Popen(args=command, stdout=st, stderr=st, stdin=st)

        output, error = proc.communicate()
        code = proc.returncode
        return code, output, error
    except OSError as error:
        return -1, '', error


def copy_content_and_children(page, new_page):
    new_page.copy_content_from(page)
    for child in page.get_children():
        copy_page_with_parent(child, new_page)
    return new_page


def copy_page_with_parent(page, parent):
    new_page = Page.objects.create(
        title=page.title, slug=page.slug, parent=parent, active=False)
    return copy_content_and_children(page, new_page)


def copy_tree(page):
    now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    new_page = Page.objects.create(
        title='Copy of {title} on {now}'.format(title=page.title, now=now),
        slug='copy-of-{slug}-on-{now}'.format(slug=page.slug, now=now),
        parent=page.parent, active=False)
    return copy_content_and_children(page, new_page)


def youtube_embed_url(request, en_youtube_id):
    embed = 'https://www.youtube.com/embed/'
    if request and not request.path.startswith('/en/'):
        lang = request.path.split('/')[1]  # validity ensured by middleware
        youtube_id = settings.LOCALIZED_YOUTUBE_ID.get(en_youtube_id, {}).get(
            lang, en_youtube_id)
        if youtube_id == en_youtube_id:
            query_template = '?hl={lang}&cc_lang_pref={lang}&cc_load_policy=1'
            return embed + youtube_id + query_template.format(lang=lang)
    else:
        youtube_id = en_youtube_id
    return embed + youtube_id


def unmangle(text):
    return text.replace(
        '\r\n', ' ').replace(
        '&rsquo;', '’').replace(
        '&ldquo;', '“').replace(
        '&rdquo;', '”').replace(
        '&mdash;', '—').replace(
        '<br />', '<br>').replace(
        '<p>&nbsp;</p>', '').replace(
        '<p>', '').replace(
        '</p>', '').replace(
        '<br><br>', ' ').replace(
        '<br>', ' ').strip()


def unmangle_pages(pages=None):
    for page in pages or Page.objects.all():
        for content_type in page._feincms_content_types:
            for entry in page.content.all_of_type(content_type):
                for field in entry._meta.fields:
                    if isinstance(field, TextField):
                        text = getattr(entry, field.name)
                        unmangled = unmangle(text)
                        if text != unmangled:
                            setattr(entry, field.name, unmangled)
                            entry.save(update_fields=[field.name])
