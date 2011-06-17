#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4

import sys
import os
import struct
from cmd import Cmd
from subprocess import Popen 

p = Popen(['watch', 'ls']) # something long running 
# ... do other stuff while subprocess is running 
p.terminate() 

class SmsShell(Cmd):
    """
        The shell that prompt for an SMS to send
    """
    
    
    @staticmethod
    def get_terminal_size():
        """
            Try to get the terminal size in to allow left and top
            align
        """
        def ioctl_GWINSZ(fd):
            try:
                import fcntl, termios
                cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
            '1234'))
            except ImportError:
                return None
            return cr
        cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
        if not cr:
            try:
                fd = os.open(os.ctermid(), os.O_RDONLY)
                cr = ioctl_GWINSZ(fd)
                os.close(fd)
            except:
                pass
        if not cr:
            try:
                cr = (env['LINES'], env['COLUMNS'])
            except:
                cr = (25, 80)
        return int(cr[1]), int(cr[0])

    
    def __init__(self, phone_number="+1234567890", *args, **kwargs):
        Cmd.__init__(self, *args, **kwargs)
        self.phone_number = phone_number 
        self.prompt = "%s >>> " % phone_number
        self.p = Popen(['tail', '-f', '/home/kevin/Bureau/test.txt']) 
        
    
    def do_EOF(self, command):    
        """
            Exit the shell.
        """
        print
        self.p.terminate()
        sys.exit(0)
    
        
    def default(self, command):
        """
            Send the message as an sms
        """
        print "<<< %s" % command
    
    
    def emptyline(self):
        """
            Do nothing if the user enter nothing.
        """

if __name__ == "__main__":
    
    
    
    shell = SmsShell()
    shell.cmdloop()
