// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef TSUKIHIME_PORT_CONFIG_H
#define TSUKIHIME_PORT_CONFIG_H

#ifndef PORT_APP_NAME
#define PORT_APP_NAME "Tsukihime"
#endif
#ifndef PORT_APP_VERSION
#define PORT_APP_VERSION "01.06"
#endif

#ifdef PORT_PLUS_DISC
#define PORT_DATA_ROOT "ux0:data/tsukihime_plus_disc"
#define PORT_FALLBACK_LOG "ux0:data/tsukihime_plus_disc-startup.log"
#else
#define PORT_DATA_ROOT "ux0:data/tsukihime"
#define PORT_FALLBACK_LOG "ux0:data/tsukihime-startup.log"
#endif
#define PORT_GAME_DIR PORT_DATA_ROOT "/game"
#define PORT_SAVE_DIR PORT_DATA_ROOT "/save"
#define PORT_STARTUP_LOG PORT_DATA_ROOT "/startup.log"

#endif
