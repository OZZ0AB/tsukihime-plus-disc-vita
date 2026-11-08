cmake_minimum_required(VERSION 3.16)

# This project builds a native Vita executable through VitaSDK. It intentionally
# packages the selected LiveArea artwork; game scripts, archives and music are
# loaded from the user's data directory.
if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
  if(DEFINED ENV{VITASDK})
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VITASDK}/share/vita.toolchain.cmake" CACHE PATH "VitaSDK toolchain")
  else()
    message(FATAL_ERROR "Set VITASDK to a VitaSDK installation before configuring this project.")
  endif()
endif()

project(TsukihimeVita LANGUAGES C CXX)

include("${VITASDK}/share/vita.cmake" REQUIRED)

set(TSUKIHIME_EDITION "plus-disc" CACHE STRING "Game to build: original or plus-disc")
set_property(CACHE TSUKIHIME_EDITION PROPERTY STRINGS original plus-disc)
if(TSUKIHIME_EDITION STREQUAL "plus-disc")
  set(TSUKIHIME_APP_NAME "Tsukihime Plus Disc")
  set(TSUKIHIME_TITLE_ID "TSUPL0001")
  set(TSUKIHIME_VERSION "01.01")
  set(TSUKIHIME_PACKAGE_NAME "TsukihimePlusDiscVita")
  set(TSUKIHIME_DELIVERY_NAME "TsukihimePlusDiscVita-Release.vpk")
  set(TSUKIHIME_LIVEAREA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/assets/plus-disc-livearea")
elseif(TSUKIHIME_EDITION STREQUAL "original")
  set(TSUKIHIME_APP_NAME "Tsukihime")
  set(TSUKIHIME_TITLE_ID "TSUKI0001")
  set(TSUKIHIME_VERSION "01.06")
  set(TSUKIHIME_PACKAGE_NAME "TsukihimeVita")
  set(TSUKIHIME_DELIVERY_NAME "TsukihimeVita-${TSUKIHIME_VERSION}.vpk")
  set(TSUKIHIME_LIVEAREA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/assets/livearea")
else()
  message(FATAL_ERROR "Unknown TSUKIHIME_EDITION: ${TSUKIHIME_EDITION}")
endif()

add_subdirectory(engine/src/onsjh)
target_compile_definitions(onsjh PRIVATE
  PORT_APP_NAME="${TSUKIHIME_APP_NAME}"
  PORT_APP_VERSION="${TSUKIHIME_VERSION}")
if(TSUKIHIME_EDITION STREQUAL "plus-disc")
  target_compile_definitions(onsjh PRIVATE PORT_PLUS_DISC FORCE_1BYTE_CHAR)
endif()
set(TSUKIHIME_VPK "${CMAKE_BINARY_DIR}/${TSUKIHIME_PACKAGE_NAME}.vpk")

# VitaSDK's macro changed the custom-target name in CMake 3.20.
if(${CMAKE_VERSION} VERSION_LESS "3.20.0")
  set(TSUKIHIME_RUNTIME_TARGET onsjh.self)
else()
  set(TSUKIHIME_RUNTIME_TARGET onsjh.self-self)
endif()

add_custom_target(vpk
  COMMAND vita-mksfoex
    -s APP_VER=${TSUKIHIME_VERSION}
    -s TITLE_ID=${TSUKIHIME_TITLE_ID}
    "${TSUKIHIME_APP_NAME}"
    "${CMAKE_BINARY_DIR}/param.sfo"
  COMMAND vita-pack-vpk
    -s "${CMAKE_BINARY_DIR}/param.sfo"
    -b "${CMAKE_BINARY_DIR}/engine/src/onsjh/onsjh.self"
    -a "${TSUKIHIME_LIVEAREA_DIR}/icon0.png=sce_sys/icon0.png"
    -a "${TSUKIHIME_LIVEAREA_DIR}/bg.png=sce_sys/livearea/contents/bg.png"
    -a "${TSUKIHIME_LIVEAREA_DIR}/startup.png=sce_sys/livearea/contents/startup.png"
    -a "${TSUKIHIME_LIVEAREA_DIR}/template.xml=sce_sys/livearea/contents/template.xml"
    "${TSUKIHIME_VPK}"
  COMMAND ${CMAKE_COMMAND} -E copy
    "${TSUKIHIME_VPK}" "${CMAKE_BINARY_DIR}/${TSUKIHIME_DELIVERY_NAME}"
  DEPENDS ${TSUKIHIME_RUNTIME_TARGET}
  COMMENT "Packaging the native Tsukihime Vita VPK"
  VERBATIM
)
