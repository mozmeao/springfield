# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import threading

from jinja2 import DictLoader, Environment

from springfield.jinja2 import ThreadSafeIncludeContentsExtension

COMPONENTS = {
    "components/box.html": "[{{ name }}|{{ contents.slot }}]",
    "components/outer.html": "[outer|{{ contents.slot }}]",
}


def build_environment(extension):
    return Environment(loader=DictLoader(COMPONENTS), extensions=[extension])


# FUTURE: remove when django-includecontents releases a new version which fixes
#         django-includecontents#11.
class TestThreadSafeIncludeContentsExtension:
    def test_concurrent_renders_do_not_leak_slot_content(self):
        """
        Slot content must land in the component that captured it, not whichever
        component happens to be rendering in another thread.

        django-includecontents 4.0.1 keeps a single ``_render_stack`` list on the
        extension instance, and Jinja2 builds one extension per Environment. So
        two threads rendering components at once push and pop frames on the same
        list, and ``<content:...>`` blocks get written to ``stack[-1]``, which
        may belong to the other thread.

        This interleaving is forced with events rather than sleeps so the test is
        deterministic:

            1. A pushes its frame and blocks inside its <content:slot> body.
            2. B pushes its frame, captures its own slot, and blocks. A's frame
               is no longer on top of the shared stack.
            3. A finishes its slot body and captures. If the stack was shared, the
               write would land in B's frame: A loses its slot, B gets A's content.
        """
        env = build_environment(ThreadSafeIncludeContentsExtension)

        a_inside_slot = threading.Event()
        b_frame_pushed = threading.Event()
        a_finished = threading.Event()

        def gate_a():
            a_inside_slot.set()
            assert b_frame_pushed.wait(timeout=10), "B never pushed its frame"
            return ""

        def gate_b():
            b_frame_pushed.set()
            assert a_finished.wait(timeout=10), "A never finished rendering"
            return ""

        # Make gate_a and gate_b accessible to the templates
        env.globals.update(gate_a=gate_a, gate_b=gate_b)

        template_a = env.from_string(
            """<include:box name="A">
              <content:slot>{{ gate_a() }}A-SLOT</content:slot>
            </include:box>"""
        )
        template_b = env.from_string(
            """<include:box name="B">
              <content:slot>B-SLOT</content:slot>
              {{ gate_b() }}
            </include:box>"""
        )

        results = {}

        def render(key, template):
            results[key] = template.render().strip()

        thread_a = threading.Thread(target=render, args=("a", template_a))
        thread_b = threading.Thread(target=render, args=("b", template_b))

        thread_a.start()
        assert a_inside_slot.wait(timeout=10), "A never reached its slot body"
        thread_b.start()
        thread_a.join(timeout=10)
        a_finished.set()
        thread_b.join(timeout=10)

        assert results["a"] == "[A|A-SLOT]"
        assert results["b"] == "[B|B-SLOT]"

    def test_nested_components_share_a_render_stack(self):
        """
        Nesting relies on the outer and inner renders seeing the same stack.

        Components render in an overlay environment, and Jinja's ``Extension.bind``
        shallow-copies the extension for it. The thread-local stack has to be shared
        across those copies the way the original list was.
        """
        env = build_environment(ThreadSafeIncludeContentsExtension)
        template = env.from_string(
            """<include:outer>
              <content:slot><include:box name="inner">
                <content:slot>DEEP</content:slot>
              </include:box></content:slot>
            </include:outer>"""
        )

        assert template.render().strip() == "[outer|[inner|DEEP]]"

    def test_repeated_renders_do_not_accumulate_stack_frames(self):
        """
        A worker thread is reused across requests, so the stack must be clear after
        every render.
        """
        env = build_environment(ThreadSafeIncludeContentsExtension)
        template = env.from_string(
            """<include:box name="A">
              <content:slot>SLOT</content:slot>
            </include:box>"""
        )

        for _ in range(3):
            assert template.render().strip() == "[A|SLOT]"

        extension = env.extensions[ThreadSafeIncludeContentsExtension.identifier]
        assert extension._render_stack == []
