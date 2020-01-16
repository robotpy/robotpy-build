from delocate.delocating import filter_system_libs
from delocate.libsana import tree_libs
from delocate.tools import set_install_name as _set_install_name

from os import path
import glob

def list_files(startpath):
    import os
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print('{}{}'.format(subindent, f))

def get_build_dependencies(build_path: str) -> list:
    """Finds the dependecies of all library files under build_path (recursive).

    :param build_path: Path to the package in the build directory (".../build/package/")
    :type build_path: str

    :return: dependencies in the form: [ ('file' : [files it wants]) ]
    :rtype: list
    """

    # import code
    # code.interact(local=dict(globals(), **locals()))

    #Build Tree of all dependencies
    build_deps = tree_libs(build_path)

    #Discard System Dependencies
    our_build_deps = []
    for key in build_deps:
        if filter_system_libs(key):
            for k, v in build_deps[key].items():
                our_build_deps.append( [k,v] )

    #Make sure 'files it wants' is a list
    for elem in our_build_deps:
        if isinstance( elem[1], str ):
            elem[1] = [elem[1]]
    
    return our_build_deps

def find_all_libs(build_path: str) -> dict:
    """ Finds all .dylib files in package
    """
    return { 
        path.basename(lib) : lib for lib in 
            glob.glob(
                path.join(
                    build_path,
                    '**/*.dylib'
                ),
                recursive=True
            )
        }

def find_libs(build_path: str, libs_folder: str = 'lib') -> dict:
    """Find .dylib files in lib folder in package
    """
    return find_all_libs( path.join( build_path, libs_folder ) )


def get_build_path(ext_fullname: str, build_lib: str) -> str:
    """Finds the path to the build directory

    :param ext_fullname: Ex. 'wpiutil._wpiutil'
    :type ext_fullname: str

    :param build_lib: Ex. '.../build'
    :type build_lib: str

    :return: Build Path -> Ex. '.../build/wpiutil'
    :rtype: str
    """
    # Ex. ext_fullname = 'wpiutil._wpiutil
    # Ex. build_lib = '.../build'

    modpath = ext_fullname.split('.')
    package = '.'.join(modpath[:-1])
    build_path = path.join(build_lib, package) # Ex. ".../build/wpiutil"

    return build_path 

def set_install_name(file: str, old_install_name: str, new_install_name: str):
    """Change the install name for a library

    :param file: path to a executable/library file
    :type file: str

    :param old_install_name: current path to dependency
    :type old_install_name: str

    :param new_install_name: new path to dependency
    :type old_install_name: str
    """

    # This function just calls delocate's set_install_name which uses install_name_tool.
    # This function exists in case we want to change the implementation.

    _set_install_name(file, old_install_name, new_install_name)
    print(file, ':', old_install_name, '->', new_install_name)



def redirect_links(build_path: str, path_map: dict, dependencies: list = None, approximate: bool = True, auto_detect: bool = True, supress_errors = False):
    """Redirects links to libraries

    :param build_path: Build Path (into package) -> Ex. '.../build/wpiutil'
    :type build_path: str

    :param path_map:
        A mapping of library names to library paths (relative paths)
        If a path is bookended by '@', then it is treated as an absolute path.
        Ex. 'lib/libwpiutil.dylib' -> '.../wpilib/../wpilib/lib/libwpiutil.dylib'
        Ex. '@lib/libwpiutil.dylib@' -> 'lib/libwpiutil.dylib'
    :type path_map: dict

    :param dependencies:
        dependencies in the form: [ ('file' : [files it wants]) ],
        If None, it will generate them from build_path,
        Defaults to None
    :type dependencies: list, optional

    :param approximate:
        If True, it will match the basename (Ex. 'libwpiutil.dylib') of library
        paths instead of full library paths. This allows for this function to
        be called multiple times on the same library (aslong as the basename
        doesn't change).
        Defaults to True

    :type approximate: bool, optional

    :param auto_detect:
        If True, attempt to automatic find library files.
        Defaults to True
    
    :type auto_detect: bool, optional

    :param suppress_errors:
        Optional, Defaults to False
    :type suppress_errors: bool

    :raises: not if you're good

    """

    auto_detected_dependencies = find_all_libs(build_path) if auto_detect else {}
    print(auto_detected_dependencies)

    if dependencies is None:
        dependencies = get_build_dependencies(build_path)
        print(dependencies)

    for dependency in dependencies:
        library_file_path = dependency[0]
        desired_files = dependency[1]
        
        rel_path = path.relpath(build_path, library_file_path) #Relative path to site-packages (essentially)

        for desired_file in desired_files:
            df_search_name = path.basename(desired_file) if approximate else desired_file

            path_to_desired_file = path_map.get(df_search_name, None)
            if path_to_desired_file is None:
                abs_path_to_df = auto_detected_dependencies.get(
                    path.basename(df_search_name),
                    None
                )

                if abs_path_to_df is None:
                    if supress_errors: continue
                    raise KeyError('Path to `' + desired_file + '` not found')

                path_to_desired_file = path.relpath(
                    abs_path_to_df, 
                    path.join(
                        build_path,
                        '..'
                    )
                )


            if path_to_desired_file is None:
                if supress_errors: continue
                raise KeyError('Path to `' + desired_file + '` not found')

            if len(path_to_desired_file) == 0:
                if supress_errors: continue
                raise ValueError('Invalid Path of 0 length')

            # Treat as absolute path if bookended by '@'
            if path_to_desired_file[0] == '@' and path_to_desired_file[-1] == '@':
                if len(path_to_desired_file) < 3:
                    if supress_errors: continue
                    raise ValueError('Invalid Absolute Path of 0 length')
                path_to_desired_file = path_to_desired_file[ 1: -1]
                set_install_name(
                    library_file_path,
                    desired_file,
                    path_to_desired_file
                )
            else:
                set_install_name(
                    library_file_path,
                    desired_file,
                    path.join('@loader_path', rel_path, path_to_desired_file)
                )