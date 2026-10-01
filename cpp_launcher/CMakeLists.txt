cmake_minimum_required(VERSION 3.20)
project(cod2_mapping_launcher LANGUAGES CXX)

if(NOT WIN32)
    message(FATAL_ERROR "This launcher currently supports Windows only.")
endif()

add_executable(cod2_mapping_launcher WIN32 main.cpp app.rc)
target_compile_features(cod2_mapping_launcher PRIVATE cxx_std_17)
target_compile_definitions(cod2_mapping_launcher PRIVATE UNICODE _UNICODE)
target_link_libraries(cod2_mapping_launcher PRIVATE shell32 user32)