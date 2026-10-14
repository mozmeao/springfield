# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Create the draft CMS scaffold for the French /features/free-pdf-editor/, from pdf-free-fr.html.

This page is unlike the English ones here: its content only ever existed in French. There is no
English source to translate from and no en-US page worth creating, so it is authored directly in
the `fr` locale and targets no other. The French below is verbatim from the template.
"""

from springfield.cms.management.commands._page_scaffold import CreatePageCommand, PageSpec, build_screenshot_block, build_text_block
from springfield.cms.models import ArticleDetailPage

HOME_URL = "/fr/"

# These screenshots also appear on /features/complete-pdf/. import_static_image() reuses an image
# by title, so both commands must build the title the same way or the second to run would import a
# duplicate.
PDF_SCREENSHOT_DIRECTORY = "img/firefox/features/edit-pdf"


def build_pdf_screenshot(block_id: str, file_stem: str) -> dict:
    return build_screenshot_block(block_id, f"{PDF_SCREENSHOT_DIRECTORY}/{file_stem}.png", f"PDF editor screenshot: {file_stem}")


def build_fields() -> dict:
    """pdf-free-fr.html — filling in the Cerfa 13750*07 vehicle registration form."""
    return {
        "index_page_heading": "Éditeur PDF gratuit pour remplir un formulaire",
        "search_description": (
            "Découvrez comment utiliser l’éditeur PDF de Firefox avec un mode d’emploi simple et bref pour "
            "remplir, modifier et archiver vos démarches en ligne"
        ),
        "description": (
            "Découvrez comment utiliser l’éditeur PDF de Firefox avec un mode d’emploi simple et bref pour "
            "remplir, modifier et archiver vos démarches en ligne"
        ),
        "content": [
            build_text_block(
                "free-pdf-intro",
                "<p>Pas si simple de remplir un formulaire administratif  en ligne, surtout quand ça demande beaucoup "
                "d’informations et que les délais sont serrés. Pas de panique !  L'éditeur PDF Firefox est là pour "
                "vous simplifier la vie.</p>"
                "<p>Prenons l’exemple d’une démarche en ligne courante, si vous possédez une voiture : comment "
                "immatriculer son véhicule, par le biais du formulaire Cerfa 13750*07.</p>",
            ),
            build_text_block(
                "free-pdf-cerfa",
                "<h2>Faire sa demande Cerfa 13750*07 grâce à un éditeur PDF simple et gratuit</h2>"
                "<p>Pour immatriculer votre véhicule, il est nécessaire de faire une demande auprès des autorités. Vous "
                "pouvez facilement trouver le formulaire vierge Cerfa 13750*07 en ligne.</p>"
                "<ol>"
                "<li><b>Ouvrir le formulaire :</b> Ouvrez le formulaire Cerfa 13750*07 sur votre ordinateur avec Firefox "
                "en faisant un clic droit et en sélectionnant “Ouvrir avec Firefox”. Le document s'affiche dans un "
                "onglet de votre navigateur.</li>"
                "<li><b>Remplir les informations nécessaires :</b> Cliquez sur l'icône Texte pour ajouter vos informations "
                "personnelles et les détails du véhicule directement sur le formulaire. Ajustez les blocs de texte et "
                "déplacez-les selon vos besoins.</li>"
                "<li><b>Cocher des cases :</b> Utilisez l'outil Dessin pour cocher les cases appropriées sur le "
                "formulaire.</li>"
                "<li><b>Signer :</b> Pour signer au bas de la demande, cliquez sur l'icône Dessin et ajoutez votre "
                "signature.</li>"
                "<li><b>Enregistrer et soumettre :</b> Une fois complété, enregistrez le document en cliquant sur l'icône "
                "Dossier. Donnez un nouveau nom à votre fichier et soumettez-le en ligne avec les autres pièces demandées "
                "ou imprimez-le pour l'envoyer par courrier.</li>"
                "</ol>",
            ),
            build_pdf_screenshot("free-pdf-shot-ouvrir", "fr-edit-pdf-ouvrir"),
            build_pdf_screenshot("free-pdf-shot-modifier", "fr-edit-pdf-modifier"),
            build_pdf_screenshot("free-pdf-shot-dessin", "fr-edit-pdf-dessin"),
            build_text_block(
                "free-pdf-securite",
                "<h2>Adoptez la simplicité et la sécurité avec l'éditeur PDF Firefox</h2>"
                "<p>Faire ses demandes administratives en ligne devient une option de plus en plus répandue ; encore "
                "faut-il pouvoir compter sur un éditeur PDF pratique, gratuit pour accomplir vos démarches en toute "
                "tranquillité !</p>"
                "<p>Que ce soit pour gérer des demandes liées à votre voiture, l’état civil, la santé, le travail, "
                "l’éditeur PDF Firefox facilite la modification de vos documents PDF sans les risques associés à "
                "l'utilisation de plateformes en ligne inconnues.</p>"
                "<p>Ne laissez plus la complexité des formulaires administratifs vous stresser.</p>"
                "<p>Découvrez comment Firefox peut rendre vos tâches quotidiennes plus simples et plus sécurisées.</p>",
            ),
            build_text_block(
                "free-pdf-cta",
                f'<p><a href="{HOME_URL}">Téléchargez Firefox</a> dès aujourd\'hui et reprenez le contrôle de vos documents PDF !</p>',
            ),
        ],
    }


class Command(CreatePageCommand):
    help = "Create the draft CMS scaffold for the French /features/free-pdf-editor/."

    # No ftl_relative_paths and no target locales: the content only ever existed in French, so the
    # page is authored in `fr` and translates to nothing.
    spec = PageSpec(
        slug="free-pdf-editor",
        page_model=ArticleDetailPage,
        parent_slugs=("features",),
        title="Utiliser un éditeur PDF gratuit",
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
