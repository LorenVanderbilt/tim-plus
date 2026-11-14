The course select's map pictures (2026-11-12), captured from the game with the frame hidden:

  *_full.png   256 x 128   the game's own size (the arcade course select)
  *_90.png     231 x 117   as the console shows them now: shrunk by the hardware (CARD_SIZE 230 in patch 020, a
                           little taller: CARD_V_EXTRA 3 in patch 040 - the frame's bars cover the extra)

The 90% ones are what the hardware's shrink makes (whole rows and columns dropped), which is why text drawn in
the pictures got hard to read. A cleaned-up 90% picture would go into the game as new graphics shown at full
size (no hardware shrink) - same size as *_90.png. Tell Claude when they're ready.

Colours: these are screenshots (full colour). A Neo Geo sprite tile has 15 colours plus transparent; the maps use
several palettes - keep to the colours already in each picture and the import can map them back.

Captured without the course records (best time and initials): the game draws those into the text layer over the
maps' bottom edge every frame, so in the game they still show on top of whatever the pictures have there.
