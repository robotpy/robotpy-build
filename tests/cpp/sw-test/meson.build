project('sw-test', ['cpp'],
        default_options: ['warning_level=1', 'cpp_std=c++20',
                          'b_colorout=auto', 'optimization=2', 'b_pie=true'])

subdir('semiwrap')

swtest_ft__ft_sources += files(
  'src/swtest/ft/src/fields.cpp',
  'src/swtest/ft/src/ft.cpp',
  'src/swtest/ft/src/using2.cpp',
)

subdir('semiwrap/modules')
