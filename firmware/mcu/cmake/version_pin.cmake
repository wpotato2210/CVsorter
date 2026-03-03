set(PINNED_GCC_VERSION "13.2.0")
set(PINNED_CMAKE_VERSION "3.27.7")
set(PINNED_NEWLIB_VERSION "4.3.0")

function(version_pin_validate)
  if(NOT CMAKE_VERSION VERSION_EQUAL PINNED_CMAKE_VERSION)
    message(FATAL_ERROR "CMake version mismatch. Required ${PINNED_CMAKE_VERSION}, got ${CMAKE_VERSION}.")
  endif()
endfunction()
