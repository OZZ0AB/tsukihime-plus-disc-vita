// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef TSUKIHIME_SAVE_MENU_LAYOUT_H
#define TSUKIHIME_SAVE_MENU_LAYOUT_H

namespace tsukihime {

// Reserve two header rows and a 16-pixel margin at each screen edge. The game
// uses 20 slots: at 640x480 this gives an 18-pixel font with 20-pixel rows.
inline int saveMenuFontSize(int slots, int screen_height)
{
    if (slots < 1) slots = 1;
    const int pitch = (screen_height - 32) / (slots + 2);
    int size = pitch - 2;
    if (size > 26) size = 26;
    if (size < 16) size = 16;
    return size;
}

} // namespace tsukihime
#endif
