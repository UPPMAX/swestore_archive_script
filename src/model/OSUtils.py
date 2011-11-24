'''
Created on Apr 4, 2011

@author: samuel
'''

import os, subprocess
from model.AbstractObject import AbstractObject 

class OSUtils(AbstractObject):
    def __init__(self):
        super(OSUtils, self).__init__()
    
    def exec_piped_command(self, cmd1, cmd2, cmd1stdin=None):
        self.log.debug("Executing piped command: %s | %s" % (cmd1, cmd2))
        
        try:
            if cmd1stdin is None:
                proc1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
                proc2 = subprocess.Popen(cmd2, stdin=proc1.stdout, stdout=subprocess.PIPE)
                commandoutput = proc2.communicate()[0]
            else:
                cmd1str = " ".join(cmd1)
                cmd2str = " ".join(cmd2)
                cmdstr = "%s | %s" % (cmd1str, cmd2str)
                proc2 = subprocess.Popen(cmdstr, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
                commandoutput = proc2.communicate(input=cmd1stdin)[0] #TODO: set the input variable, in the right way
    
            commandoutput = commandoutput.rstrip("\n")
            
            returncode = proc2.returncode
            errmsg = proc2.stderr
            
            if returncode != 0:
                raise Exception("Return code from command was not zero! Error message: %s" % errmsg)
        except Exception, e:
            self.log.error("Piped command failed: %s | %s\nError message:" % (" ".join(cmd1), " ".join(cmd2)))
            self.log.error(str(e)) 
            raise
        
        return commandoutput
        
        
    def exec_command(self, cmd, exception_on_nonzero_return_code=True, cmd1stdin=None):
        self.log.debug("Executing command: %s" % " ".join(cmd))
    
        try:
            if cmd1stdin is None:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (stdout, errmsg) = proc.communicate()
            else:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                (stdout, errmsg) = proc.communicate(input=cmd1stdin)
                
            stdout = stdout.rstrip("\n")
    
            if exception_on_nonzero_return_code and proc.returncode != 0:
                raise Exception("Error when executing command: %s\n*** STDERR: ***\n  %s\n*** STDOUT: ***\n  %s" % (" ".join(cmd), errmsg, stdout))
    
            self.log.debug("Output from command: %s" % stdout)
        
        except Exception, e: 
            self.log.error(str(e))
            raise
    
        return (stdout, errmsg, proc.returncode)

        