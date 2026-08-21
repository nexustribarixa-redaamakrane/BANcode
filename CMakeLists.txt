cmake_minimum_required(VERSION 3.20)
project(bancode
    VERSION 1.0.0
    LANGUAGES C
    DESCRIPTION "BANcode Framework - diagnostic code registry for bare-metal OS kernels"
)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# Static library target
add_library(bancode STATIC
    kernel_src/bancode/bancode.c
    kernel_src/bancode/bancode_trap.c
)

target_include_directories(bancode
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/kernel_inc
)

# Compiler-specific flags
if(MSVC)
    target_compile_options(bancode PRIVATE /W4 /WX)
else()
    target_compile_options(bancode PRIVATE
        -std=c99 -ffreestanding -nostdlib
        -Wall -Wextra -Werror -Wpedantic
    )
endif()

# Ensure output is libbancode.a (or bancode.lib on MSVC)
set_target_properties(bancode PROPERTIES
    OUTPUT_NAME bancode
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
)

# Custom target: regenerate from .txt sources
find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_FOUND)
    add_custom_target(generate
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/parse_sources.py
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_bindings.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        COMMENT "Parsing .txt sources and generating bindings..."
    )
else()
    add_custom_target(generate
        COMMAND python ${CMAKE_CURRENT_SOURCE_DIR}/scripts/parse_sources.py
        COMMAND python ${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_bindings.py
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        COMMENT "Parsing .txt sources and generating bindings..."
    )
endif()

# Custom target: build everything (generate + compile)
add_custom_target(full
    DEPENDS generate bancode
    COMMENT "Full pipeline: parse -> generate -> compile"
)

# Install target
install(TARGETS bancode
    ARCHIVE DESTINATION lib
)
install(DIRECTORY kernel_inc/bancode
    DESTINATION include
)

# Symbol audit target (GCC/Clang only)
if(NOT MSVC)
    add_custom_target(audit
        COMMAND ${CMAKE_COMMAND} -E echo "=== Symbol audit: checking for hosted runtime symbols ==="
        COMMAND sh -c "nm $<TARGET_FILE:bancode> | grep -E 'U (printf|malloc|free|exit|abort|fprintf|fopen|fclose|fread|fwrite|calloc|realloc|memcpy|memset|memmove|strcmp|strlen|strncpy|strcpy|puts|putchar|getchar|stdin|stdout|stderr)' && echo 'FAIL: hosted symbols found' || echo 'PASS: no hosted symbols'"
        DEPENDS bancode
        COMMENT "Auditing libbancode.a for hosted runtime symbols"
    )
    enable_testing()
    add_test(
        NAME symbol_audit
        COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --target audit
    )
endif()
