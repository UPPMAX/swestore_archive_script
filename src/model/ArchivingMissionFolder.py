'''
Created on Apr 4, 2011

@author: samuel
'''

from model.Folder import Folder

class ArchivingMissionFolder(Folder):
    def __init__(self, arch_mssn, path):
        super(ArchivingMissionFolder, self).__init__(path)

        self.arch_mssn = arch_mssn
        self.project_folder = arch_mssn.project.folder
        self.path = path