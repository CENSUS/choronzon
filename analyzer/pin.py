#!/usr/bin/env python

'''
    pin.py provides a driver class for Intel's binary
    instrumentation framework PIN. The exposed API allows a
    user to trace and monitor the execution of any given binary
    executable image, including shared libraries.
'''

import platform
import os
import sys
import time
import shlex
import signal
import subprocess
import threading
import ctypes
import random

EVENT_ALL_ACCESS = 0x1F0003
EVENT_MODIFY_STATE = 0x0002

NMPWAIT_USE_DEFAULT_WAIT = 0x0
NMPWAIT_WAIT_FOREVER = 0xFFFFFFFF

class PinRunner(object):
    '''
        Base PIN driver class. It provides a generic interface
        to PIN's functionality. This includes the execution of a
        binary under PIN's monitoring and the injection of any pintool
        in the process.
    '''
    pintool = None
    cmd_template = None
    process = None
    timeout = None
    event_name = None
    timer = None

    def __init__(self, timeout=20):
        self.timeout = timeout
        if platform.system() == 'Linux':
            self.cmd_template = 'pin -t %s %s'
        elif platform.system() == 'Windows':
            self.cmd_template = 'pin.exe -t %s %s'


    def handler(self):
        '''
            the signal/event alarm handler. This code is executed
            when the alarm is off.
        '''
        if self.process.poll() != None:
            return
        try:
            if platform.system() == 'Linux':
                self.process.send_signal(signal.SIGUSR2)
            elif platform.system() == 'Windows':
                event_object = ctypes.windll.kernel32.OpenEventA(
                                    EVENT_ALL_ACCESS, False, self.event_name)

                ctypes.windll.kernel32.SetEvent(event_object)
        except OSError, ex:
            print '[!] ERROR: ', ex

    def set_alarm(self, seconds=None):
        '''
            sets a therad timer that calls the handler() function.
        '''
        if seconds == None:
            return

        if self.timer != None:
            self.timer.cancel()

        self.timer = threading.Timer(float(seconds), self.handler)
        self.timer.start()

    def craft_command(self, pintool, arguments=''):
        '''
            creates a command string based on the user settings,
            default values for the platform and the specified
            target binary.
        '''
        if not pintool:
            raise ValueError('pintool not provided')
        if not os.path.exists(pintool):
            raise IOError(
                    'pintool %s does not exist'
                    % pintool
                    )
        cmd = None
        if platform.system() == 'Linux':
            cmd = shlex.split(
                self.cmd_template % (pintool, arguments)
                )
        elif platform.system() == 'Windows':
            cmd = self.cmd_template % (pintool, arguments)
        return cmd

    def run(self, pintool, *args):
        '''
            runs the user-provided pintool with a user-provided
            argument list.
        '''
        pintool_args = None
        if args and type(args) == tuple:
            pintool_args = ' '.join(args)
        else:
            pintool_args = ''
        # craft command string
        cmd = self.craft_command(pintool, pintool_args)
        # call pin with

        try:
            self.set_alarm(self.timeout)

            with open(os.devnull, 'w') as nullfp:
                print 'Calling: %s' % cmd
                self.process = subprocess.Popen(cmd,
                                    stdout=nullfp, stderr=nullfp)

            ### self.process.wait()

        except subprocess.CalledProcessError:
            return

class Coverage(PinRunner):
    '''
        This is a specific PIN module that is optimized to be
        used with the coverage.so pintool that accompanies Choronzon.
        It makes use of OS provided pipes and events to collect
        the execution information as quickly as possible.
    '''
    def __init__(self,
            pintool='analyzer/coverage/obj-intel64/coverage.so',
            timeout=20
            ):
        self.pintool = os.path.abspath(pintool)
        super(Coverage, self).__init__(timeout)

    def _run(self, execmd, output, whitelist):
        '''
            execmd is the command string to run
            the pintool on.
        '''
        # if os.path.exists(output):
        #    os.remove(output)

        quoted_whilelist = []
        for image in whitelist:
            quoted_whilelist.append('\"%s\"' % os.path.basename(image))

        # print '[+] Running pintool...'
        if platform.system() == 'Linux':
            return super(Coverage, self).run(
                    self.pintool,
                    '-o %s -wht %s -- %s'
                    % (output, ' -wht '.join(quoted_whilelist), execmd)
                    )
        elif platform.system() == 'Windows':
            self.event_name = 'Global\\event%s' % str(
                    random.randint(0, 0xFFFFFFFFFFFFFFFF)
                    )
            return super(Coverage, self).run(
                    self.pintool,
                    '-o %s -e %s -wht %s -- %s'
                    % (
                        output,
                        self.event_name,
                        ' -wht '.join(quoted_whilelist),
                        execmd
                        )
                )

    def _pre_run(self, output):
        if platform.system() == 'Linux':
            os.mkfifo(output)

    def _post_run(self, output):
        if platform.system() == 'Windows':
            ready = 0
            while not ready:
                ready = ctypes.windll.kernel32.WaitNamedPipeA(
                        output,
                        NMPWAIT_USE_DEFAULT_WAIT
                    )

    def run(self, execmd, output='output.dmp', whitelist=[]):
        basename_output = output
        if platform.system() == 'Windows':
            output = '\\\\.\\pipe\\%s' % basename_output
        self._pre_run(output)
        self._run(execmd, basename_output, whitelist)
        self._post_run(output)

        return output

