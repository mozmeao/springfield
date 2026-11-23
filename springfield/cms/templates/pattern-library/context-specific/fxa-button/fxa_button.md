The `fxa_button` component links to Mozilla account sign-up. Its URL carries an entrypoint built from the UTM source and campaign, which is also sent as utm_source, plus utm_medium=referral and the utm_campaign. On pages that don't supply UTM parameters, the campaign is derived from the label.

Editors add it as the Firefox Account Button wherever buttons are allowed. It has the usual theme and icon settings but no link field — the destination is always account sign-up.
