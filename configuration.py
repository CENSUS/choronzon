'''
    Provides a singleton class that initializes and stores
    all the settings for the currently loaded campaign. It is
    shared with all of Choronzon's components.
'''

import os
import sys
import imp
import contextlib

class Singleton(type):
    '''
        Basic singleton class recipe. Use this as a
        metaclass for any other normal class definition and
        it will become a singleton.
    '''
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(Singleton, cls).__call__(*args, **kwargs)
            return cls.__instance

class Configuration(object):
    '''
        Singleton that provides a uniform API for Choronzon's
        components to look up various settings and configurations.
    '''
    __metaclass__ = Singleton

    def __init__(self, configfile):
        if not os.path.exists(configfile):
            raise IOError('Configuration file does not exist.')

        self.configfile = os.path.abspath(configfile)
        self.module = self.import_program_as_module('%s' % self.configfile)

    def __contains__(self, item):
        try:
            getattr(self.module, item)
            return True
        except AttributeError:
            return False

    @contextlib.contextmanager
    def preserve_value(self, namespace, name):
        """ A context manager to preserve, then restore, the specified binding.

            :param namespace: The namespace object (e.g. a class or dict)
                containing the name binding.
            :param name: The name of the binding to be preserved.
            :yield: None.

            When the context manager is entered, the current value bound to
            `name` in `namespace` is saved. When the context manager is
            exited, the binding is re-established to the saved value.

            """
        saved_value = getattr(namespace, name)
        yield
        setattr(namespace, name, saved_value)


    def make_module_from_file(self, module_name, module_filepath):
        """
            Make a new module object from the source code in specified file.

            :param module_name: The name of the resulting module object.
            :param module_filepath: The filesystem path to open for
                reading the module's Python source.
            :return: The module object.

            The Python import mechanism is not used. No cached bytecode
            file is created, and no entry is placed in `sys.modules`.

        """
        py_source_open_mode = 'U'
        py_source_description = (".py", py_source_open_mode, imp.PY_SOURCE)

        with open(module_filepath, py_source_open_mode) as module_file:
            with self.preserve_value(sys, 'dont_write_bytecode'):
                sys.dont_write_bytecode = True
                module = imp.load_module(
                        module_name, module_file, module_filepath,
                        py_source_description)

        return module


    def import_program_as_module(self, program_filepath):
        """
            Import module from program file `program_filepath`.

            :param program_filepath: The full filesystem path to the program.
                This name will be used for both the source file to read, and
                the resulting module name.
            :return: The module object.

            A program file has an arbitrary name; it is not suitable to
            create a corresponding bytecode file alongside. So the creation
            of bytecode is suppressed during the import.

            The module object will also be added to `sys.modules`.

        """
        module_name = os.path.basename(program_filepath)

        module = self.make_module_from_file(module_name, program_filepath)
        sys.modules[module_name] = module

        return module

    def __getitem__(self, name):
        return getattr(self.module, name)

    def __setitem__(self, name, value):
        setattr(self.module, name, value)


class ConfigurationError(Exception):
    '''
        Exception for errors in the configuration file.
    '''
    pass
