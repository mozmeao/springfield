/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
  Loaded site-wide behind the `easter-egg-emoji-rain` waffle switch. Visitors
  arriving from the Toronto engineering summit stickers
  (`?utm_team=web+martech`) get a short shower of Toronto, Canada and Firefox
  emojis falling down the page. To retire the easter egg, flip the switch off.
*/

const TRIGGER_PARAM = 'utm_team';
// `URLSearchParams` decodes the `+` in the sticker URL to a space.
const TRIGGER_VALUE = 'web martech';

const EMOJIS = [
    // Toronto
    '🦝', // Raccoon, the city's unofficial "trash panda" mascot
    '🚋', // Streetcar, the red TTC streetcars
    '🏙️', // City skyline
    '🗼', // Tower, standing in for the CN Tower (the emoji is Tokyo Tower)
    '🏒', // Hockey stick, for the Maple Leafs
    '🦖', // Dinosaur, for the Raptors
    '🐦', // Bird, for the Blue Jays
    // Canada
    '🍁', // Maple leaf
    '🇨🇦', // Canadian flag
    '🦫', // Beaver
    '🪿', // Goose, for the famously aggressive Canada geese
    '🫎', // Moose
    '☕', // Coffee, a Tim Hortons nod
    '🍩', // Donut, another Tim Hortons nod
    '🍟', // Fries, the closest thing to poutine
    '❄️', // Snowflake
    // Firefox
    '🦊', // Fox
    '🔥', // Fire
    '🌐' // Globe, for the open web
];

const RAIN_DURATION_MS = 10000;
const SPAWN_INTERVAL_MS = 120;
const MIN_FALL_DURATION_MS = 4000;
const MAX_FALL_DURATION_MS = 8000;
const MIN_FONT_SIZE_PX = 20;
const MAX_FONT_SIZE_PX = 44;
const MAX_HORIZONTAL_DRIFT_PX = 80;

function randomBetween(min, max) {
    return min + Math.random() * (max - min);
}

function randomEmoji() {
    return EMOJIS[Math.floor(Math.random() * EMOJIS.length)];
}

/**
 * Returns `true` when the query string carries the summit sticker's
 * `utm_team` value.
 */
function isWebMartechVisit(search) {
    return new URLSearchParams(search).get(TRIGGER_PARAM) === TRIGGER_VALUE;
}

function createRainContainer() {
    const container = document.createElement('div');
    container.className = 'easter-egg-emoji-rain';
    container.setAttribute('aria-hidden', 'true');
    Object.assign(container.style, {
        position: 'fixed',
        inset: '0',
        overflow: 'hidden',
        pointerEvents: 'none',
        zIndex: '10000'
    });
    return container;
}

/**
 * Drops a single emoji from above the viewport to below it and removes it
 * once it has fallen out of view.
 */
function dropEmoji(container) {
    const emoji = document.createElement('span');
    emoji.textContent = randomEmoji();
    Object.assign(emoji.style, {
        position: 'absolute',
        top: '0',
        left: `${randomBetween(0, 100)}%`,
        fontSize: `${randomBetween(MIN_FONT_SIZE_PX, MAX_FONT_SIZE_PX)}px`,
        lineHeight: '1',
        // Start above the viewport so emojis don't pop into existence.
        transform: 'translateY(-100%)'
    });
    container.appendChild(emoji);

    const drift = randomBetween(
        -MAX_HORIZONTAL_DRIFT_PX,
        MAX_HORIZONTAL_DRIFT_PX
    );
    const rotation = randomBetween(-360, 360);
    const fall = emoji.animate(
        [
            { transform: 'translate(0, -100%) rotate(0deg)' },
            {
                transform: `translate(${drift}px, calc(100vh + 100%)) rotate(${rotation}deg)`
            }
        ],
        {
            duration: randomBetween(MIN_FALL_DURATION_MS, MAX_FALL_DURATION_MS),
            easing: 'linear',
            fill: 'forwards'
        }
    );
    fall.onfinish = () => emoji.remove();
}

/**
 * Spawns falling emojis for `RAIN_DURATION_MS`, then removes the container
 * after the last emoji has fallen out of view.
 */
function startEmojiRain() {
    const container = createRainContainer();
    document.body.appendChild(container);

    const spawnTimer = setInterval(
        () => dropEmoji(container),
        SPAWN_INTERVAL_MS
    );

    setTimeout(() => {
        clearInterval(spawnTimer);
        setTimeout(() => container.remove(), MAX_FALL_DURATION_MS);
    }, RAIN_DURATION_MS);

    return container;
}

function initEmojiRain() {
    if (!isWebMartechVisit(window.location.search)) {
        return;
    }
    if (
        window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
        return;
    }

    startEmojiRain();
}

initEmojiRain();
