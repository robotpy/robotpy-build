project('swtest-base', ['cpp'],
        default_options: ['warning_level=1', 'cpp_std=c++20',
                          'b_colorout=auto', 'optimization=2', 'b_pie=true'])

subdir('semiwrap')

swtest_base__module_sources += files(
  'src/swtest_base/cpp/main.cpp',
)

swtest_base__module2_sources += files(
  'src/swtest_base/cpp/main2.cpp',
)

swtest_base__module3_sources += files(
  'src/swtest_base/cpp/main3.cpp',
)

subdir('semiwrap/modules')
