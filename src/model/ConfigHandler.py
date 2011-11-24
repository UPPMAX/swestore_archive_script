'''
Created on Apr 29, 2011

@author: samuel
'''

import ConfigParser

class ConfigHandler(object):
    '''
    classdocs
    '''
    
    options = {}
    option_names = []

    def __init__(self):
        '''
        Constructor
        '''
        self.option_names = [
                                  'swestoreuploaduid',
                                  'swestoreuploadgid',
                                  'projects_path',
                                  'drop_folder_path_rel',
                                  'confirm_files_path_rel',
                                  'uploadcache_path',
                                  'startarchiving_filename',
                                  'projectname_pattern', 
                                  'allowedfilename_pattern', 
                                  'excludedfilename_pattern',
                                  'arch_mssn_id_pattern', 
                                  'swestorebasepath', 
                                  'tarexcludepatternsfile', 
                                  'daystowaitbeforeupload', 
                                  'createtempfolder_retries',
                                  'createtempfolder_waittime',
                                  'uploadretries',
                                  'uploadretry_waittime',
                                  'chunk_size_in_mb',
                                  'logfile', 
                                  'logging_level', 
                                  'ngcp_debug_level',
                                  'create_par2_files',
                                  'par2_bin_path'
                               ]
    
    def init_from_file(self, configfile_path):
        config_parser = ConfigParser.SafeConfigParser()
        config_parser.read(configfile_path)
        
        for option_name in self.option_names:
            self.options[option_name] = config_parser.get('main', option_name)
