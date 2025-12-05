/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Firefox logo entity for Draftail rich text editor
// This powers the fx-logo feature implemented in springfield/cms/wagtail_hooks.py

class FXLogoSource extends window.React.Component {
    componentDidMount() {
        const { editorState, entityType, onComplete } = this.props;

        const content = editorState.getCurrentContent();
        const selection = editorState.getSelection();

        const contentWithEntity = content.createEntity(
            entityType.type,
            'IMMUTABLE',
            {}
        );

        const entityKey = contentWithEntity.getLastCreatedEntityKey();

        // Insert a ZERO WIDTH JOINER (U+200D) character with the entity
        // This is a non-whitespace character that Draft.js won't strip
        // It's commonly used for emoji sequences and is invisible
        const newContent = window.DraftJS.Modifier.replaceText(
            contentWithEntity,
            selection,
            '\u200D',
            null,
            entityKey
        );

        const nextState = window.DraftJS.EditorState.push(
            editorState,
            newContent,
            'insert-characters'
        );

        onComplete(nextState);
    }

    render() {
        return null;
    }
}

function FXLogo(props) {
    'use strict';

    // The decorator displays the Firefox logo in the editor
    // It wraps the non-breaking space with a styled span
    // The styles need to match those from media/css/cms/flare26-typography.css
    return window.React.createElement(
        'span',
        {
            className: 'fl-fx-logo',
            style: {
                display: 'inline-block',
                width: '1em',
                height: '1em',
                backgroundImage:
                    'url(/media/img/logos/firefox/firefox-logo.svg)',
                backgroundSize: 'contain',
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'center',
                verticalAlign: 'middle',
                color: 'transparent',
                marginInline: '0.1em'
            }
        },
        props.children
    );
}

window.draftail.registerPlugin(
    {
        type: 'FX-LOGO',
        source: FXLogoSource,
        decorator: FXLogo
    },
    'entityTypes'
);
