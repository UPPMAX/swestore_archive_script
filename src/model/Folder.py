'''
Created on Apr 4, 2011

@author: samuel
'''

import os, re
from model.Resource import Resource
from model.File import File

class Folder(Resource):
    def __init__(self, path):
        super(Folder, self).__init__(path)

    
    def ensure_exists(self):
        if not self.exists():
            self.log.info("Folder does not exist, so creating: %s" % self.path)
            self.create()
    
    
    def create(self, mode=None):
        try:
            if mode is None:
                os.makedirs(self.path)
            else:
                os.makedirs(self.path, mode)
        except:
            self.log.error("Could not create directory: %s" % self.path)
            raise
        
    
    def get_size(self):
        return self.recursively_get_folder_size(self.path)
    

    def recursively_get_folder_size(self, folder):
        tot_size_of_curr_folder = os.path.getsize(folder)

        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            if os.path.isfile(item_path):
                tot_size_of_curr_folder += os.path.getsize(item_path)
            elif os.path.isdir(item_path):
                tot_size_of_curr_folder += self.recursively_get_folder_size(item_path)
        
        return tot_size_of_curr_folder
    
    
    def list_files(self):
        try:
            result_paths = os.listdir(self.path)
            return result_paths
        except Exception:
            self.log.error("Could not list files in folder %s" % self.path)
            raise
        

    def list_files_recursive(self, include_self=False):
        def list_files_recursive_sub(folder, rel_base_path):
            result_paths = []
            items = os.listdir(folder)
            if len(items) > 0:
                for item in items:
                    full_path = os.path.join(folder, item)
                    rel_path = os.path.join(rel_base_path, item)
                    result_paths.append(rel_path)
                    if os.path.isdir(full_path):
                        subpaths = list_files_recursive_sub(full_path, rel_path)
                        result_paths.extend(subpaths)
            return result_paths
        
        if include_self:
            return list_files_recursive_sub(self.path, self.name)
        else:
            return list_files_recursive_sub(self.path, "")
        
    
    def get_files_matching_pattern(self, pattern, antipattern="", recursive=False, only_empty_folders=False):

        '''Method used as a more secure alternative to "glob". It returns all files in 
        the specified folders (except files in subfolders), whose filenames match the
        specified regex pattern'''
        
        result_files = []
        
        if recursive:
            files = self.list_files_recursive()
        else:
            files = self.list_files()
        
        try:
            for file_name in files:
                if (re.match(pattern, file_name) and antipattern == "") or (re.match(pattern, file_name) and not re.match(antipattern, file_name)):
                    file_path = os.path.join(self.path, file_name)
                    # Only include empty folders
                    is_dir = os.path.isdir(file_path)
                    dir_is_empty = False
                    if is_dir:
                        dir_is_empty = (len(os.listdir(file_path)) == 0)
                    if os.path.isfile(file_path):
                        file = File(file_path)
                        result_files.append(file)
                    elif (is_dir and (not only_empty_folders or (only_empty_folders and dir_is_empty))):
                        folder = Folder(file_path)
                        result_files.append(folder)
                        
                    
        except Exception:
            self.log.error("Could not get files in folder %s, matching pattern %s (antipattern %s)" % (self.path, pattern, antipattern))
            raise
        
        return result_files