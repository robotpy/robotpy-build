project('sw-caster-consumer', ['cpp'],
        default_options: ['warning_level=1', 'cpp_std=c++20',
                          'b_colorout=auto', 'optimization=2', 'b_pie=true'])

subdir('semiwrap')

sw_caster_consumer__module_sources += files(
  'src/sw_caster_consumer/cpp/main.cpp',
)

subdir('semiwrap/modules')
