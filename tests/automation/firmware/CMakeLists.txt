cmake_minimum_required(VERSION 3.16)
project(cvsorter_firmware_tests LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

option(ENABLE_COVERAGE "Enable gcov coverage flags" OFF)
if(ENABLE_COVERAGE)
  add_compile_options(--coverage -O0 -g)
  add_link_options(--coverage)
endif()

find_package(GTest QUIET)
if(NOT GTest_FOUND)
  message(FATAL_ERROR "GoogleTest not found. Install GTest to run firmware tests.")
endif()

enable_testing()

add_executable(firmware_logic_tests
  test_firmware_logic_gtest.cpp
  ../../../firmware/mcu/src/scheduler.c
  ../../../firmware/mcu/src/command_dispatch.c
  ../../../firmware/mcu/src/watchdog.c
)

target_include_directories(firmware_logic_tests PRIVATE
  ../../../firmware/mcu/include
  ../../../firmware/mcu/config
)

target_link_libraries(firmware_logic_tests PRIVATE GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(firmware_logic_tests)
