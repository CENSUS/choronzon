#!/usr/bin/env python

'''
    disassembler.py provides an interface to IDA Pro's
    functionality. This module exposes a class that can disassemble
    a given binary into a list of basic blocks, using IDA's command
    line interface.
'''

import os
import platform
import subprocess

class Disassembler(object):
    '''
        This is the disassembler's base class.
    '''
    disassembler_path = None
    def __init__(self, dispath):
        # The path to disassembler binary
        self.disassembler_path = dispath
        if not os.path.exists(dispath):
            raise IOError('Disassembler could not be found at %s' % dispath)

    def get_disassembler_path(self):
        '''
            Returns the path of the disassembler's binary.
        '''
        return self.disassembler_path

    def disassemble(self, binary, output):
        '''
            This method should be overridden with the implemention of each
            disassembler.
        '''
        raise NotImplementedError(
            'Do not call this method of this class directly.')

class IDADisassembler(Disassembler):
    '''
        A generic IDA Pro CLI driver class.
    '''
    def get_ida_runnable(self, exe):
        '''
            returns the appropriate IDA binary according to
            platform and target architecture.
        '''
        system = platform.system()
        # platform.architecture = arch, linkage
        arch, _ = platform.architecture(
                exe,
                bits='64bit'
                )

        runnable = ''
        if system == 'Linux':
            runnable = 'idal'
        elif system == 'Windows':
            runnable = 'idaw'
        else:
            raise OSError('Unsupported system "%s".' % system)

        if arch == '64bit':
            runnable += '64'
        if system == 'Windows':
            runnable += '.exe'

        return runnable

    def _run_ida(self, exe, script='', output='.'):
        '''
            crafts the command and executes it in order to
            retrieve the list of basic blocks given a binary.
        '''
        xecut = self.get_ida_runnable(exe)
        ida = os.path.join(self.disassembler_path, xecut)
        scriptcmd = '%s -o %s' % (script, output)
        script = os.path.abspath(script)

        cmdlist = []
        cmdlist.append(ida) # first argument, ida's path
        cmdlist.append('-A')
        cmdlist.append('-L"%s"' % os.path.join(output, "log.txt"))
        cmdlist.append('-S"%s"' % scriptcmd)
        cmdlist.append('%s' % exe)

        print '[-] command line: ', ' '.join(cmdlist)

        proc = None
        if platform.system() == 'Linux':
            proc = subprocess.Popen(' '.join(cmdlist), shell=True)
        elif platform.system() == 'Windows':
            proc = subprocess.Popen(' '.join(cmdlist))

        proc.wait()

    def disassemble(self, blob, output='.'):
        '''
            wrapper that calls the appropriate functions in
            order to expose the class' functionality.
        '''
        self._run_ida(blob, 'disassembler/prepare.py', output)

        dump = os.path.join(output, '%s.idmp' % blob)

        with open(dump, 'r') as fin:
            for line in fin:
                yield line
