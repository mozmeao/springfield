/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

document.addEventListener("DOMContentLoaded", async () => {
  // If user prefers reduced motion, we don't do anything. 
  // Video won't play and no animation. Instead the static poster will be shown.
  const userPrefersReducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  if (userPrefersReducedMotion.matches) return;

  const shell = document.querySelector(".ios-phone-shell");
  const video = shell?.querySelector("video");
  if (!shell || !video) return;

  const shakeAnimation = () => shell.classList.add("shake");
  const removeShakeAnimation = () => shell.classList.remove("shake");

  video.addEventListener("playing", shakeAnimation, { once: true });

  let prev = 0;
  video.addEventListener("timeupdate", () => {
    if (prev > 0.1 && video.currentTime < 0.1) shakeAnimation();
    prev = video.currentTime;
  });

  shell.addEventListener("animationend", removeShakeAnimation);

  try {
    await video.play();
  } catch (e) { 
    // Something went wrong. For now, we do nothing.
  }
});