'''
Created on Apr 4, 2011

@author: samuel
'''

from model.AbstractObject import AbstractObject

class AbstractDomain(AbstractObject):
    def __init__(self, name):
        super(AbstractDomain, self).__init__()