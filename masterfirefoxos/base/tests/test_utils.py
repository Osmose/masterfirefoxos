import os
from unittest.mock import Mock, patch

from django.test import override_settings, RequestFactory

from feincms.module.page.models import Page

from .. import models
from .. import utils


def test_entry_strings():
    rich_text_entry = models.RichTextEntry(
        title='title', subheader_2='sub 2', subheader_3='sub 3', text='test text')
    assert utils.entry_strings(rich_text_entry) == ['title', 'sub 2', 'sub 3', 'test text']

    image_paragraph_entry = models.ImageParagraphEntry(
        alt='alt', title='test title', text='test text',
        subheader_2='sub 2', subheader_3='sub 3')
    assert set(utils.entry_strings(image_paragraph_entry)) == set([
        'alt', 'test title', 'test text', 'sub 2', 'sub 3'])

    faq_entry = models.FAQEntry(
        question='test question', answer='test answer')
    assert utils.entry_strings(faq_entry) == [
        'test question', 'test answer']

    youtube_entry = models.YouTubeParagraphEntry(
        title='test title', text='test text', youtube_id='test id',
        subheader_2='sub 2', subheader_3='sub 3')
    assert set(utils.entry_strings(youtube_entry)) == set([
        'test title', 'test text', 'sub 2', 'sub 3'])


@patch('masterfirefoxos.base.utils.copy_content_and_children')
@patch('masterfirefoxos.base.utils.Page.objects')
@patch('masterfirefoxos.base.utils.datetime')
def test_copy_tree(mock_datetime, mock_page_objects,
                   mock_copy_content_and_children):
    mock_datetime.now().strftime.return_value = 'date'
    parent = Page()
    page = Page(title='foo bar', slug='sl-ug', active=True, parent=parent)
    assert (utils.copy_tree(page) ==
            mock_copy_content_and_children.return_value)
    mock_page_objects.create.assert_called_with(
        title='Copy of foo bar on date', slug='copy-of-sl-ug-on-date',
        parent=parent, active=False)
    mock_copy_content_and_children.assert_called_with(
        page, mock_page_objects.create.return_value)


@patch('masterfirefoxos.base.utils.copy_content_and_children')
@patch('masterfirefoxos.base.utils.Page.objects')
def test_copy_page_with_parent(mock_page_objects,
                               mock_copy_content_and_children):
    page = Page(title='title', slug='slug', active=False)
    assert (utils.copy_page_with_parent(page, 'parent') ==
            mock_copy_content_and_children.return_value)
    mock_page_objects.create.assert_called_with(
        title='title', slug='slug', parent='parent', active=False)
    mock_copy_content_and_children.assert_called_with(
        page, mock_page_objects.create.return_value)


@patch('masterfirefoxos.base.utils.copy_page_with_parent')
def test_copy_content_and_children(mock_copy_page_with_parent):
    page = Mock()
    page.get_children.return_value = ['child']
    new_page = Mock()
    assert utils.copy_content_and_children(page, new_page) == new_page
    new_page.copy_content_from.assert_called_with(page)
    mock_copy_page_with_parent.assert_called_with('child', new_page)


@override_settings(LOCALIZED_YOUTUBE_ID={
                   'en-youtube-id': {'xx': 'xx-youtube-id'}})
def test_youtube_embed_url_translated_id():
    request = RequestFactory().get('/xx/introduction/')
    expected = 'https://www.youtube.com/embed/xx-youtube-id'
    assert utils.youtube_embed_url(request, 'en-youtube-id') == expected


def test_youtube_embed_url_subtitle_querystring():
    request = RequestFactory().get('/xx/introduction/')
    expected = ('https://www.youtube.com/embed/en-youtube-id' +
                '?hl=xx&cc_lang_pref=xx&cc_load_policy=1')
    assert utils.youtube_embed_url(request, 'en-youtube-id') == expected


def test_youtube_embed_url_en():
    request = RequestFactory().get('/en/introduction/')
    expected = 'https://www.youtube.com/embed/en-youtube-id'
    assert utils.youtube_embed_url(request, 'en-youtube-id') == expected


def test_page_strings():
    page = Page(title='page title')
    rich_text_entry = models.RichTextEntry(
        title='title', subheader_2='sub 2', subheader_3='sub 3', text='test text')
    faq_entry = models.FAQEntry(
        question='test question', answer='test answer')

    page._feincms_content_types = [Mock()]
    page.content.all_of_type = lambda type: [rich_text_entry, faq_entry]

    assert set(utils.page_strings(page)) == set([
        'page title', 'title', 'sub 2', 'sub 3', 'test text', 'test question',
        'test answer'])


TEST_VERSIONS_LOCALE_MAP = {
    'v1': {
        'locales': ['fr', 'pt-BR'],
        'pending_locales': ['es'],
        'slug': 'v1',
    },
    'v2': {
        'locales': ['fr', 'sl'],
        'slug': 'v2',
    },
}


@override_settings(VERSIONS_LOCALE_MAP=TEST_VERSIONS_LOCALE_MAP)
def test_versions_for_locale():
    assert set(utils.versions_for_locale('fr')) == set(['v1', 'v2'])
    assert set(utils.versions_for_locale('sl')) == set(['v2'])
    assert set(utils.versions_for_locale('es')) == set(['v1'])


@override_settings(VERSIONS_LOCALE_MAP=TEST_VERSIONS_LOCALE_MAP)
def test_all_versions():
    assert set(utils.all_versions()) == set(['v1', 'v2'])


def base_path(*parts):
    return os.path.join(os.sep, 'app', *parts)


@override_settings(BASE_DIR=base_path())
def test_versions_po_filename():
    assert (utils.versions_po_filename('es', ['v1'])
            == base_path('locale', 'es', 'LC_MESSAGES', 'firefox_os_v1.po'))
    assert (utils.versions_po_filename('pt-br', ['v2'], template=True)
            == base_path('locale', 'pt_BR', 'LC_MESSAGES', 'firefox_os_v2.pot'))
    assert (utils.versions_po_filename('es', ['z2', 'v1'])
            == base_path('locale', 'es', 'LC_MESSAGES', 'firefox_os_v1_z2.po'))


@override_settings(BASE_DIR=base_path())
def test_po_filename():
    assert (utils.po_filename('es', 'messages')
            == base_path('locale', 'es', 'LC_MESSAGES', 'messages.po'))
    assert (utils.po_filename('pt-br', 'template', template=True)
            == base_path('locale', 'pt_BR', 'LC_MESSAGES', 'template.pot'))


@override_settings(BASE_DIR=base_path())
def test_locale_dir():
    assert utils.locale_dir('es') == base_path('locale', 'es')
    assert utils.locale_dir('pt-br') == base_path('locale', 'pt_BR')
    assert utils.locale_dir('en-US') == base_path('locale', 'en_US')


@override_settings(BASE_DIR=base_path())
def test_po_filenames_for_locale():
    with patch('masterfirefoxos.base.utils.glob') as mock_glob:
        mock_glob.return_value = ['/app/test.po', '/app/test2.po', '/app/django.po']
        assert (set(utils.po_filenames_for_locale('es'))
                == set(['/app/test.po', '/app/test2.po']))
        mock_glob.assert_called_with(base_path('locale', 'es', '**', '*.po'))


def test_execute():
    with patch('masterfirefoxos.base.utils.subprocess') as mock_subprocess:
        proc = mock_subprocess.Popen.return_value
        proc.returncode = 0
        proc.communicate.return_value = 'output', 'error'

        assert utils.execute(['foo', 'bar']) == (0, 'output', 'error')
        pipe = mock_subprocess.PIPE
        mock_subprocess.Popen.assert_called_with(
            args=['foo', 'bar'], stdout=pipe, stderr=pipe, stdin=pipe)


def test_execute_oserror():
    with patch('masterfirefoxos.base.utils.subprocess') as mock_subprocess:
        error = OSError('Could not find file')
        mock_subprocess.Popen.side_effect = error

        assert utils.execute(['foo', 'bar']) == (-1, '', error)
