# WeFiles portrait source

`source.png` is the user-supplied 6-column, 5-row portrait sheet (1024 × 765),
copied unchanged from the supplied attachment. No faces are regenerated.

The catalog and exact cell boundaries are in `accounts/avatars.py`. The
`avatar_art` template tag in `accounts/templatetags/accounts_ui.py` renders whole cells with 18 source pixels of white
safe space on every side. A proportional outer SVG contains the complete
cell; the inner viewport hides neighboring cells. This avoids cover crops,
circular clipping, stretching, and selection badges covering the portrait.

Some artwork already reaches or is cut off by the source sheet's cell edges.
Padding prevents additional clipping; it cannot reconstruct missing artwork.
Use an uncropped original if exact missing hair/head details must be restored.

Original SHA-256: `81991d2fbf12e8f62b607a0e1189303271d5d9ba508bfa30ca2a8bade8937a6d`
