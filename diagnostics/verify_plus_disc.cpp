// SPDX-License-Identifier: GPL-2.0-or-later
#include "ScriptHandler.h"
#include "DirectReader.h"
#include "sjis2utf16.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>

SJIS2UTF16 encoding;
Coding2UTF16 *coding2utf16 = &encoding;

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    encoding.init();
    std::string root = std::string(argv[1]) + "/";
    ScriptHandler script;
    script.reset();
    if (script.openScript(&root[0])) return 1;
    assert(script.screen_width == 640 && script.screen_height == 480);
    const char *labels[] = {"start", "main_menu", "load_menu", "gallery_0",
                            "story_0", "story_1", "story_2", "story_3"};
    for (const char *label : labels) assert(script.lookupLabel(label).label_header);

    char *cursor = script.getAddress(0);
    unsigned texts = 0;
    while ((cursor = std::strstr(cursor, "\nputtext `"))) {
        cursor += std::strlen("\nputtext ");
        const char *end = std::strchr(cursor + 1, '`');
        assert(end);
        const std::string expected(cursor, end - cursor);
        script.setCurrent(cursor);
        assert(std::strcmp(script.readStr(), expected.c_str()) == 0);
        assert(script.getEndStatus() & ScriptHandler::END_1BYTE_CHAR);
        assert(*script.getNext() == '\n');
        cursor = const_cast<char *>(end + 1);
        ++texts;
    }
    assert(texts > 4000);
    DirectReader files(&root[0]);
    assert(files.getFileLength("default.ttf") > 1024);
    assert(files.getFileLength("plus-disc-data.json") > 1024);
    std::printf("Production reader: 640x480, eight entry labels, %u puttext strings, font and data manifest: OK\n", texts);
}
