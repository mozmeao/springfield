# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Create the draft CMS scaffold for the French /features/complete-pdf/, from pdf-complete-fr.html.

This page is unlike the English ones here: its content only ever existed in French. There is no
English source to translate from and no en-US page worth creating, so it is authored directly in
the `fr` locale and targets no other. The French below is verbatim from the template.
"""

from springfield.cms.management.commands._page_scaffold import CreatePageCommand, PageSpec, build_screenshot_block, build_text_block
from springfield.cms.models import ArticleDetailPage

PDF_EDITOR_URL = "/fr/features/pdf-editor/"
FEATURES_URL = "/fr/features/"
HOME_URL = "/fr/"

# These screenshots also appear on /features/free-pdf-editor/. import_static_image() reuses an
# image by title, so both commands must build the title the same way or the second to run would
# import a duplicate.
PDF_SCREENSHOT_DIRECTORY = "img/firefox/features/edit-pdf"


def build_pdf_screenshot(block_id: str, file_stem: str) -> dict:
    return build_screenshot_block(block_id, f"{PDF_SCREENSHOT_DIRECTORY}/{file_stem}.png", f"PDF editor screenshot: {file_stem}")


def build_fields() -> dict:
    """pdf-complete-fr.html — filling in a French tax declaration."""
    return {
        "index_page_heading": "Remplir un PDF en ligne: fiche d’impôts",
        "search_description": (
            "Retrouvez un guide pas-à-pas pour remplir et même corriger sa déclaration d’impôts, en utilisant les options intégrées de Firefox."
        ),
        "description": (
            "Retrouvez un guide pas-à-pas pour remplir et même corriger sa déclaration d’impôts, en utilisant les options intégrées de Firefox."
        ),
        "content": [
            build_text_block(
                "complete-pdf-intro",
                "<p>Fini les soucis liés à la paperasse, place à la simplicité administrative !  Que vous ayez besoin de "
                "remplir une première déclaration, de corriger une erreur ou de gérer vos justificatifs, Firefox vous "
                "offre une solution rapide et sécurisée pour vos données. </p>"
                "<p>Remplir des PDF n'a jamais été aussi simple et fiable, même quand on parle de fiches d’impôts.</p>",
            ),
            build_text_block(
                "complete-pdf-remplir",
                "<h2>Remplir sa PDF</h2>"
                "<p>Renseigner les informations de manière électronique plutôt que de le faire à la main pour éviter les "
                "erreurs, les reprises et un procédé administratif qui traine. C’est d’autant plus à portée de main "
                "si c’est votre première déclaration fiscale ! </p>"
                "<ol>"
                "<li><b>Ouvrir le document :</b> une fois le formulaire vierge téléchargé, faites un clic droit dessus et "
                'sélectionnez "Ouvrir avec Firefox". Le document apparaît dans un onglet de votre navigateur.</li>'
                "<li><b>Renseigner vos informations :</b> Cochez  les cases appropriées à l’aide de l’outil Dessin "
                "symbolisé par un crayon.</li>"
                "<li><b>Pour ajouter du texte :</b> cliquez sur l'icône Texte pour ajouter du texte tels que votre numéro "
                "fiscal, vos noms, adresse et autre renseignements fiscaux. </li>"
                "</ol>",
            ),
            build_pdf_screenshot("complete-pdf-shot-ouvrir", "fr-edit-pdf-ouvrir"),
            build_pdf_screenshot("complete-pdf-shot-texte", "fr-edit-pdf-texte"),
            build_text_block(
                "complete-pdf-deplacer",
                "<p>Vous pouvez déplacer n’importe quel de vos blocs de texte et ajuster la taille, comme bon vous "
                "semble. Vous pouvez facilement passer d’une page à l’autre de votre déclaration ou avoir une vue "
                "d’ensemble en sélectionnant dans les Outils. </p>",
            ),
            build_pdf_screenshot("complete-pdf-shot-modifier", "fr-edit-pdf-modifier"),
            build_text_block(
                "complete-pdf-corriger",
                "<p>Enregistrez le document une fois terminé et envoyez-le aux services fiscaux en suivant les "
                "instructions.</p>"
                "<p>Si vous souhaitez corriger une déclaration :  suivez les mêmes étapes pour ouvrir et "
                f"<a href=\"{PDF_EDITOR_URL}\">remplir votre PDF</a> avec Firefox. N'oubliez pas d'ajouter la mention "
                '"DÉCLARATION RECTIFICATIVE, ANNULE ET REMPLACE" en haut de votre formulaire. </p>'
                "<p>Faites les corrections nécessaires, enregistrez le nouveau fichier et envoyez-le selon les "
                "instructions.</p>",
            ),
            build_text_block(
                "complete-pdf-archiver",
                "<h2>Enregistrer sa déclaration au format PDF</h2>"
                "<p>L’éditeur PDF Firefox vous aide à remplir mais aussi à classer et archiver vos tâches "
                "administratives, en toute confidentialité.</p>"
                "<p>Vous pouvez organiser vos justificatifs comme les factures, les reçus de dons, et l’imprimé fiscal "
                "unique. Ces documents n'ont pas à être fournis lors de la déclaration mais doivent être conservés en cas "
                "de contrôle, pendant au moins 3 ans. Pourquoi ne pas se simplifier la tâche dès l’étape de la "
                "déclaration ? </p>"
                "<p>Enregistrez tous vos PDF dans des dossiers bien nommés pour une gestion facile et sécurisée.</p>",
            ),
            build_text_block(
                "complete-pdf-cta",
                "<h2>Vous n'avez pas encore Firefox ?</h2>"
                f'<p><a href="{FEATURES_URL}">En savoir plus</a> sur nos fonctionnalités, ou '
                f'<a href="{HOME_URL}">Téléchargez Firefox</a> dès maintenant.</p>',
            ),
        ],
    }


class Command(CreatePageCommand):
    help = "Create the draft CMS scaffold for the French /features/complete-pdf/."

    # No ftl_relative_paths and no target locales: the content only ever existed in French, so the
    # page is authored in `fr` and translates to nothing.
    spec = PageSpec(
        slug="complete-pdf",
        page_model=ArticleDetailPage,
        parent_slugs=("features",),
        title="Remplir un PDF en ligne : fiche d’impôts",
        ftl_relative_paths=(),
        target_locale_codes=(),
        build_fields=build_fields,
        source_locale_code="fr",
        editor_notes=(
            "re-apply the hide-from-firefox visibility rule to the closing call-to-action — rich text has no equivalent for that CSS class",
            "move each screenshot back beside the step it illustrates: Wagtail rich text cannot nest a block "
            "child inside a list item, so the screenshots follow their list instead",
            "give the screenshots real alt text — the old template left it empty, so they imported as decorative",
            "re-apply the data-cta-link / data-link-text analytics attributes, which rich text does not carry",
        ),
    )
