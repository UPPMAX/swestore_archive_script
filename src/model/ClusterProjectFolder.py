'''
Created on Apr 4, 2011

@author: samuel
'''

from model.Folder import Folder

class ClusterProjectFolder(Folder):
    def __init__(self, project, path):
        super(ClusterProjectFolder, self).__init__(path)
        self.project = project
        self.transfer_folders = None
        