cmake_minimum_required(VERSION 3.27.7)

project(coloursorter_mcu_firmware C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/version_pin.cmake)
version_pin_validate()

add_library(firmware_core STATIC
  src/watchdog.c
  src/brownout.c
  src/isr.c
  src/scheduler.c
  src/command_dispatch.c
  src/actuator.c
)

target_include_directories(firmware_core PUBLIC
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_SOURCE_DIR}/config
)

add_executable(firmware_main src/main.c)
target_link_libraries(firmware_main PRIVATE firmware_core)
