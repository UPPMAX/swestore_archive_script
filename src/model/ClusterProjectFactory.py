'''
Created on Apr 4, 2011

@author: samuel
'''

import re, os
from model.AbstractObject import AbstractObject
from model.ClusterProject import ClusterProject

class ClusterProjectFactory(AbstractObject):
    
    '''Domain object for keeping track of the life-cycle of cluster project
       objects, and objects they aggregate (such as project_folder objects)'''
    
    def __init__(self, archiving_domain, application):
        super(ClusterProjectFactory, self).__init__()
        
        self.app = application
        self.projects = []
        self.archiving_domain = archiving_domain
        
        
    def get_projects(self):

        new_cluster_projects = []
        
        project_folder_paths = self.get_project_folder_paths()
        for project_folder_path in project_folder_paths:
            project_name = self.extract_project_name_from_path(project_folder_path)
            self.log.info("Found project %s" % project_name)
            project = ClusterProject(project_name, self.archiving_domain)
            new_cluster_projects.append(project)
            
        if len(new_cluster_projects) == 0:
            self.log.warn("No projects found!")
            
        return new_cluster_projects
        
        
    def get_project_folder_paths(self):
        project_folder_names = []
        projects_path = self.app.config.options["projects_path"]

        try:
            action = self.archiving_domain.app.action
            # projects_path = self.app.config.options["projects_path"]
            if action in ["prepare", "createconfirmfiles"]:
                project_folder_names = os.listdir(projects_path)
            elif action == "upload":
                project_folder_names = os.listdir(self.app.config.options["uploadcache_path"])

        except:
            self.log.error("Could not list directory: %s" % projects_path)
            raise

        project_folder_paths = [] # To be returned

        if len(project_folder_names) == 0:
            self.log.warn("No project folder names found, so could not initialize projects")
        else:
            for project_folder_name in project_folder_names:
                if re.match(self.app.config.options["projectname_pattern"], project_folder_name): # Security Check
                    if action in ["prepare", "createconfirmfiles"]:
                        project_folder_path = os.path.join(self.app.config.options["projects_path"], project_folder_name)
                    elif action == "upload":
                        project_folder_path = os.path.join(self.app.config.options["uploadcache_path"], project_folder_name)
                    
                    if os.path.isdir(project_folder_path):
                        project_folder_paths.append(project_folder_path)
                    else:
                        self.log.warn("Found non-directory with matching project folder pattern: %s" % project_folder_path)
                
        return project_folder_paths
    
    
    def extract_project_name_from_path(self,project_folder_path):
        matches = re.match(".*(%s).*" % self.app.config.options["projectname_pattern"], project_folder_path)
        project_name = matches.group(1)
        return project_name
    