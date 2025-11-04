/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// From Wagtail's documentation example on creating new Draftail entities:
// https://docs.wagtail.org/en/stable/extending/extending_draftail.html#creating-new-entities
// This powers the <fxa> tag implemented in springfield/cms/wagtail_hooks.py

function uuid4() {
    'use strict';
    return '10000000-1000-4000-8000-100000000000'.replace(/[018]/g, (c) =>
        (
            +c ^
            (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))
        ).toString(16)
    );
}

class FXASource extends window.React.Component {
    componentDidMount() {
        const { editorState, entityType, onComplete } = this.props;

        const content = editorState.getCurrentContent();

        const contentWithEntity = content.createEntity(
            entityType.type,
            'MUTABLE',
            {
                uid: uuid4(),
                url: ''
            }
        );
        const selection = editorState.getSelection();
        const entityKey = contentWithEntity.getLastCreatedEntityKey();

        const originalText = content
            .getBlockForKey(selection.anchorKey)
            .getText()
            .slice(selection.getStartOffset(), selection.getEndOffset());

        const newContent = window.DraftJS.Modifier.replaceText(
            content,
            selection,
            originalText,
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

function FXA(props) {
    'use strict';
    const { entityKey, contentState } = props;
    const data = contentState.getEntity(entityKey).getData();

    return window.React.createElement(
        'a',
        {
            'data-cta-uid': data.uid
        },
        props.children
    );
}

window.draftail.registerPlugin(
    {
        type: 'FXA',
        source: FXASource,
        decorator: FXA
    },
    'entityTypes'
);
