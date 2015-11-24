Porting Translations
====================

Prior to the addition of the Puente and the `collectstrings` script,
translations were stored in a single `django.po` file per-locale, and the
`cleanup_po` script was used to remove strings that weren't necessary for
certain locales.

This following describes the steps for porting the old translation file layout
to the new one while preserving existing translations.

1. Delete the ``django.pot`` file, as well as the
   ``templates/LC_MESSAGES/django.pot`` symlink.

2. Run the extraction commands for database and template strings::

    ./manage.py extract
    ./manage.py merge
    ./manage.py runscript db_strings

3. Run the one-time import script to populate the new files using translations
   from the existing ``django.po`` files::

    ./manage.py runscript import_collected_translations

4. Delete all the remaining ``django.po`` files and add ``django.po``
   and ``django.pot`` to the ``.gitignore`` file within the locale directory.

5. Commit your changes. You're done!
