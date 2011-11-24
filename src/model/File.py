'''
Created on Apr 4, 2011

@author: samuel
'''

import os
from model.Resource import Resource
from model.OSUtils import OSUtils

class File(Resource):
    def __init__(self, path):
        super(File, self).__init__(path)
        
    def ensure_exists(self):
        if not self.exists():
            self.write("")
            
    def write(self,content):
        mode = "w" # Open file for (over)writing
        self.write_or_append(content, mode)

    def append(self,content):
        mode = "a" # Open file for appending
        self.write_or_append(content, mode)
        
    def write_or_append(self, content, mode):
        try:
            file_handle = open(self.path, mode)
        except:
            self.log.error("Could not open file for writing: %s" % self.path)
            raise

        try:
            file_handle.write(content)
        except:
            self.log.error("Could not write to file: %s" % self.path)
            raise
        
    def read(self):
        try:
            file_handle = open(self.path, "r")
        except:
            self.log.error("Could not open file for reading: %s" % self.path)
            raise

        try:
            file_content = file_handle.read()
        except:
            self.log.error("Could not read from file: %s" % self.path)
            raise

        return file_content
    
    def get_size(self):
        try:
            return os.path.getsize(self.path)
        except:
            self.log.error("Could not get size of file: %s" % self.path)
            raise
        
    def get_md5sum(self):
        getmd5sum_cmd = ["md5sum", self.path]
        try:
            (stdout, stderr, returncode) = OSUtils().exec_command(getmd5sum_cmd)
            md5sum = stdout.split(" ")[0]
        except:
            errmsg = "ERROR: Failed to get md5sum of file: %s" % self.path
            self.log.error(errmsg)
            raise Exception(errmsg)
        return md5sum
    
    def get_adler32sum(self):
        getadler32sum_cmd = ["jacksum", "-a", "adler32", "-F", "#CHECKSUM", self.path]
        try:
            (stdout, stderr, returncode) = OSUtils().exec_command(getadler32sum_cmd)
            adler32sum = stdout.split(" ")[0]
        except Exception, e:
            errmsg = "ERROR: Failed to get adler32sum of file: %s\nError message:%s" % (self.path, str(e))
            self.log.error(errmsg)
            raise Exception(errmsg)
        return adler32sum    
