// SPDX-License-Identifier: GPL-2.0-or-later
#include "save_menu_layout.h"
#include "save_support.h"
#include <cassert>
#include <cstdio>
#include <cstring>

int main()
{
    const int slots = 20, width = 640, height = 480;
    const int font = tsukihime::saveMenuFontSize(slots, height);
    const int pitch = font + 2;
    const int rows = slots + 2;
    const int top = (height - rows * pitch) / 2;
    const int columns = (std::strlen("Memory") + 1) / 2 + 2 + 13;
    const int left = (width - columns * font) / 2;
    assert(font == 18 && pitch == 20 && top >= 16 && left >= 16);
    for (int slot = 1; slot <= slots; ++slot) {
        char number[5], month[5], day[5], hour[5], minute[5], text[128];
        const tsukihime::SaveTime time = {2026, 12, 31, 23, 59, 59};
        tsukihime::formatSaveNumbers(slot, time, number, month, day, hour, minute);
        const int y = top + (slot + 1) * pitch;
        // Include a full row for SDL_ttf's ascenders, descenders, and shadow.
        assert(y >= 16 && y + pitch <= height - 16);
        std::snprintf(text, sizeof(text), tsukihime::SAVE_EXIST_FORMAT,
                      "Memory", number, month, day, hour, minute);
        assert(left + static_cast<int>(std::strlen(text) - 1) * font / 2 + 2 <= width - 16);
        std::snprintf(text, sizeof(text), tsukihime::SAVE_EMPTY_FORMAT, "Memory", number);
        assert(left + static_cast<int>(std::strlen(text) - 1) * font / 2 + 2 <= width - 16);
    }
    // A long list must select a smaller font than a short menu.
    assert(tsukihime::saveMenuFontSize(9, height) > font);
    std::printf("Save/load layout: all 20 populated/empty slots and header fit 640x480; font %d, row %d, margins >=16: OK\n", font, pitch);
}
