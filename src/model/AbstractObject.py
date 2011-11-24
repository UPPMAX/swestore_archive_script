'''
Created on Apr 4, 2011

@author: samuel
'''
import logging

class AbstractObject(object):
    def __init__(self):
        self.log = self.getLogger()
        
    def getLogger(self):
        logger = logging.getLogger("default")
        return logger