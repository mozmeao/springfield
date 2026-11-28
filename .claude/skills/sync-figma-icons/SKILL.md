---
name: sync-figma-icons
description: Sync the Flare icon SVGs in media/img/firefox/flare/icons with the icons in the Firefox.com Design System Figma file, then regenerate their CSS. Use when asked to update, import or sync icons from Figma.
---

## How icons work here

- Icons are SVGs under `media/img/firefox/flare/icons/<platform>-<size>/<category>/<name>-<size>.svg`.
- Each one renders as a 1em CSS mask (`media/css/cms/components/flare-icon.css`), so it scales with the font size.
- **Keep exactly one SVG per icon.** If the same icon exists in several sizes or on both platforms (e.g. `globe-16` on desktop and `globe-24` on mobile), only one file belongs in the repo.
- Every viewBox is cropped to the icon's artwork, so all icons fill their box the same way.
- The value a CMS editor stores is the file name without its size suffix (`springfield/cms/icon_utils.py`). Never rename or delete an existing SVG: pages that use it would lose the icon.
- `manifest.json`, in this folder, records the Figma hash each icon file was last synced from.

The Figma source is the file `5ebjB97defiRGZ7C5N0Hoi`, page "↳ Atoms" (`104177:22530`). Desktop icons are in frame `112220:167270` and mobile icons in frame `112220:166233`. Load the `figma:figma-use` skill before any `use_figma` call. A View seat allows only 20 MCP calls a month, so use a Dev or Full seat (check with `whoami`).

## Steps

Use `/tmp/figma-icon-sync` as the work directory.

1. **Ask the person** whether they want a quick sync (export only icons whose Figma hash changed since the last sync, according to `manifest.json`) or a full re-download of every icon. Pass `--full` to `plan.py` for the second.

2. **Inventory.** Run this with `use_figma` (it only reads the file), then save its output, verbatim, to `/tmp/figma-icon-sync/inventory.txt`:

   ```js
   const page = await figma.getNodeByIdAsync('104177:22530');
   await figma.setCurrentPageAsync(page);
   const fnv = s => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(16); };
   const rows = [];
   for (const [platform, frameId] of [['desktop', '112220:167270'], ['mobile', '112220:166233']]) {
     const frame = await figma.getNodeByIdAsync(frameId);
     for (const icon of frame.findAll(n => n.type === 'INSTANCE' && !n.name.startsWith('_'))) {
       rows.push([platform, icon.name, icon.id, fnv(await icon.exportAsync({ format: 'SVG_STRING' }))].join('|'));
     }
   }
   return rows.join('\n');
   ```

3. **Plan.** Run `python3 -I .claude/skills/sync-figma-icons/plan.py /tmp/figma-icon-sync [--full]`. It writes `todo.json` and batches of node ids in `batches/NN.txt`.
   - Icons already in the repo update their own file.
   - An icon with no file in any size is new and gets one sample, preferring a folder that already exists.
   - Other sizes of icons already in the repo are left out.

4. **Export** each batch with `use_figma`, replacing `BATCH_LINE` with the batch file's contents:

   ```js
   const fnv = s => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(16); };
   const out = {};
   for (const id of "BATCH_LINE".split(',')) {
     const icon = await figma.getNodeByIdAsync(id);
     const svg = await icon.exportAsync({ format: 'SVG_STRING' });
     out[id] = { h: fnv(svg), svg };
   }
   return out;
   ```

   Save the result byte for byte to `/tmp/figma-icon-sync/out/NN.json`, then run `python3 -I .claude/skills/sync-figma-icons/write.py /tmp/figma-icon-sync /tmp/figma-icon-sync/out/NN.json`.
   - The script skips any SVG that doesn't match its Figma hash (a copying mistake). Re-export only the ids it lists.
   - With more than a couple of batches, hand them to subagents, a few batches each, to keep the SVG text out of your context.

5. **Crop** every viewBox to its artwork: `node .claude/skills/sync-figma-icons/crop.js tests/playwright/node_modules/playwright-core media/img/firefox/flare/icons`. It is idempotent, so running it over the whole folder is fine. It needs `npm install` and `npx playwright install chromium` in `tests/playwright`.

6. **Refresh `assets/`.** Django serves and scans `assets/` before `media/`. `npm start` copies `media/` there only once, and the copy never deletes files. So run `rm -rf assets/img/firefox/flare/icons && npm run static`. Otherwise the icon picker and the CSS generator see stale or deleted icons, and the visual regression tests screenshot the old artwork.

7. **CSS.** Run:
   1. `uv run --active python manage.py generate_flare_icon_css --icon-dir media/img/firefox/flare/icons --output /tmp/figma-icon-sync/generated.css`
   2. `python3 -I .claude/skills/sync-figma-icons/splice_css.py /tmp/figma-icon-sync/generated.css`

   - A COLLISION means two files hold the same icon. Delete the file this sync added and keep the existing one, then run both commands again. Don't add paths to `_COLLIDING_PATHS`.
   - Confirm that `git diff media/css/cms/components/flare-icon.css | grep '^-\.'` prints nothing, which means no existing rule was removed.

8. **Verify.**
   - Run `uv run --active pytest springfield/cms/tests/test_pattern_contexts.py springfield/cms/tests/test_commands.py springfield/cms/tests/test_blocks.py -k "icon or pattern" --reuse-db`.
   - Check the Base Styles → Icons page in the pattern library.
   - In `tests/playwright`, run `npm run visual-regression-tests`, review the failing diffs, and use `npm run update-snapshots` only for diffs that are the new artwork.

9. Commit `manifest.json` together with the icons and the CSS.
