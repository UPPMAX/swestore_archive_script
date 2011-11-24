'''
Created on Apr 4, 2011

@author: samuel
'''

import os
from model.AbstractObject import AbstractObject
from model.ClusterProjectFolder import ClusterProjectFolder
from model.File import File
from model.ApplicationLock import ApplicationLock

class ClusterProject(AbstractObject):
    def __init__(self, name, archiving_domain):
        super(ClusterProject, self).__init__()
        # Attributes
        self.name = name
        self.archiving_domain = archiving_domain
        self.app = self.archiving_domain.app
        
        self.folder = ClusterProjectFolder(self, os.path.join(self.app.config.options["projects_path"], self.name))
        self.drop_folder = ClusterProjectFolder(self, os.path.join(self.folder.path, self.app.config.options["drop_folder_path_rel"]))
        self.uploadcache_proj_folder = ClusterProjectFolder(self, os.path.join(self.app.config.options["uploadcache_path"], self.name))
        self.confirmation_files_folder = ClusterProjectFolder(self, os.path.join(self.folder.path, self.app.config.options["confirm_files_path_rel"]))
        self.start_archiving_file = File(os.path.join(self.drop_folder.path, self.app.config.options["startarchiving_filename"]))
        
        self.arch_mssns = []
        
    def has_start_archiving_file(self):
        return self.start_archiving_file.exists()
    
    def get_lock_for_start_archiving_file(self):
        applock = ApplicationLock(self.start_archiving_file)
        lock_succeeded = applock.lock()

        if (lock_succeeded):
            self.log.info("Successfully locked start archiving file for project %s" % self.name)
        else:
            errmsg = "Unable to lock start archiving file for project %s" % self.name
            self.log.error(errmsg)
            raise Exception(errmsg)

        return applock

    def get_arch_mssns_with_states(self, states):
        arch_mssns = []
        
        for arch_mssn in self.arch_mssns:
            for state in states:
                if arch_mssn.state == state:
                    arch_mssns.append(arch_mssn)
                    
        return arch_mssns

    