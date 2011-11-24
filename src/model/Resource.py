'''
Created on Apr 4, 2011

@author: samuel
'''

import os
from model.AbstractObject import AbstractObject

class Resource(AbstractObject):
    """Abstract class for File and Folder"""
    def __init__(self, path):
        super(Resource, self).__init__()
        self.path = path
        self.name = self.extract_last_part_of_path(path)
        
    def assert_exists(self):
        if not self.exists():
            errmsg = "Could not find %s: %s" % (self.get_type(), self.path)
            self.log.error(errmsg)
            raise Exception(errmsg)
        
    def exists(self):
        return os.path.exists(self.path)
    
    def ensure_delete(self):
        if self.exists():
            self.delete()
            
    def delete(self):
        try:
            os.remove(self.path)
        except Exception:
            self.log.error("Could not delete %s: %s" % (self.get_type(), self.path))
            raise

                
    def get_type(self):
        if os.path.isfile(self.path):
            return "file"
        elif os.path.isdir(self.path):
            return "dir"
        
    def extract_last_part_of_path(self, path):
        return os.path.basename(path.strip("/"))