'''
Created on Apr 4, 2011

@author: samuel
'''

import os
from model.AbstractObject import AbstractObject 
from model.File import File 
from model.OSUtils import OSUtils 

class FileChunk(AbstractObject):
    
    '''FileChunk objects are used to collect chunks of files and folders that 
    should go into one single tar archive.'''
    
    def __init__(self, arch_mssn):
        super(FileChunk, self).__init__()

        self.files = []
        self.size = 0
        self.should_split = False
        
        self.arch_mssn = arch_mssn
        self.app = self.arch_mssn.app
        self.chunk_no = arch_mssn.get_no_of_file_chunks() 
        self.chunk_name = "chunk%03d" % self.chunk_no
        
        self.meta_file = File(os.path.join(self.arch_mssn.uploadcache_proj_folder.path, "chunk%03d.tar.meta" % self.chunk_no))
        self.archive_file = File(os.path.join(self.arch_mssn.uploadcache_proj_folder.path, "chunk%03d.tar" % self.chunk_no))
        
        self.split_files = []
    
    def set_should_split(self):
        self.split_files = None #TODO: Implement
        
    def unset_should_split(self):
        self.meta_file = File(os.path.join(self.arch_mssn.uploadcache_proj_folder.path, "chunk%03d.tar.meta" % self.chunk_no))
        
    def add_file(self, file_or_folder):
        chunk_size_in_mb = int(self.app.config.options["chunk_size_in_mb"])
        chunk_size = chunk_size_in_mb * 1024 * 1024 # Convert to bytes
        self.files.append(file_or_folder)
        self.size += int(file_or_folder.get_size())

        if self.size > chunk_size:
            self.should_split = True
    
    def get_remaining_size(self):
        chunk_size_in_mb = int(self.app.config.options["chunk_size_in_mb"])
        chunk_size = chunk_size_in_mb * 1024 * 1024 # Convert to bytes
        remaining_size = chunk_size - self.size
        return remaining_size

    def is_empty(self):
        if len(self.files) > 0:
            return False
        else:
            return True

    def get_file_names(self):
        filenames_list = []
        if len(self.files) > 0:
            for file in self.files:
                filenames_list.append(file.name)
        else:
            self.log.warn("No files or folders found")
        
        return filenames_list
    
    def get_relative_file_paths(self):
        '''Get file paths relative to the current archiving missions' drop folder'''
        
        base_folder = self.arch_mssn.folder.path
        
        filepaths_list = []
        if len(self.files) > 0:
            for file in self.files:
                file_path = file.path
                rel_file_path = file_path.replace(base_folder + "/", "")
                filepaths_list.append(rel_file_path)
        else:
            self.log.warn("No files or folders found")
        
        return filepaths_list
        
    def get_file_names_recursive(self):
        filenames_list = []
        if len(self.files) > 0:
            for file in self.files:
                filenames_list.append(file.name)
                if file.get_type() == "dir":
                    dir_contents = file.list_files_recursive(include_self=True)
                    filenames_list.extend(dir_contents)
                    
        else:
            self.log.warn("No files or folders found")
        
        return filenames_list
    
    def get_tar_command(self):
        tar_cmd = ["tar", "-cvf", self.archive_file.path, "-C", self.arch_mssn.folder.path, "-T", "-"]
        tar_cmd.extend(["--exclude-from=" + self.app.config.options["tarexcludepatternsfile"]])
        return tar_cmd
    
    def get_tar_command_for_piping(self):
        tar_cmd = ["tar", "-cvf", "-", "-C", self.arch_mssn.folder.path, "-T", "-"]
        tar_cmd.extend(["--exclude-from=" + self.app.config.options["tarexcludepatternsfile"]])
        return tar_cmd
    
    def get_split_command(self):
        return ["split", "-b", str(self.app.config.options["chunk_size_in_mb"]) + "m", "-d", "-a", "5", "-", self.archive_file.path + ".split"]
    
    def get_archiving_file_paths(self):
        archiving_file_paths = []
        archiving_files = self.get_archiving_files()
        for archiving_file in archiving_files:
            archiving_file_paths.append(archiving_file.path)
        return archiving_file_paths
    
    def get_archiving_files(self):
        archive_files = []
        archive_files.append(self.meta_file)
        if self.should_split:
            split_files = self.get_splitted_archive_file()
            archive_files.extend(split_files)
        else:
            archive_file_unsplit = self.get_unsplit_archive_file()
            archive_files.append(archive_file_unsplit)
        return archive_files
    
    def get_unsplit_archive_file(self):
        return self.archive_file
    
    def get_splitted_archive_file(self):
        archive_file_name = self.archive_file.name
        split_files = self.arch_mssn.uploadcache_proj_folder.get_files_matching_pattern("%s.split\d{5}" % archive_file_name)
        return split_files
    
    def create_as_tar_file_in_upload_cache(self):
        files_to_archive = self.get_relative_file_paths()
        files_to_archive_as_rows = "\n".join(files_to_archive)
        files_to_archive_as_rows = files_to_archive_as_rows + "\n"
        
        if self.should_split:
            tar_cmd = self.get_tar_command_for_piping()
            split_cmd = self.get_split_command()
            try:
                OSUtils().exec_piped_command(tar_cmd, split_cmd, cmd1stdin=files_to_archive_as_rows)
                self.log.info("Tar-and-split operation successful for archive: " + self.archive_file.path)
            except:
                self.log.error("Failed tar-and-split operation for (planned) tar file: %s" % self.archive_file.path)
                raise
        elif not self.should_split:
            tar_cmd = self.get_tar_command()
            try:
                OSUtils().exec_command(tar_cmd, cmd1stdin=files_to_archive_as_rows)
            except:
                self.log.error("Failed tar operation for (planned) tar file: %s" % self.archive_file.path)
                raise
            self.log.info("Tar operation successful for archive: " + self.archive_file.path)


    def create_meta_file(self):
        metafile_content = self.get_metafile_content()
        self.log.debug("Creating meta file: " + self.meta_file.path)
        self.meta_file.write(metafile_content)
        
    def get_metafile_content(self):
        metafile_content = \
        "<?xml version=\"1.0\"?>\n" + \
        "<archivemetainfo>\n" + \
        "  <project>%s</project>\n" % self.arch_mssn.project.name + \
        "  <archiving_mission_id>%s</archiving_mission_id>\n" % self.arch_mssn.id 

        if self.should_split:
            sum_size = 0
            for split_file in self.get_splitted_archive_file():
                sum_size += split_file.get_size()
            size = sum_size 
        else:
            size = self.archive_file.get_size()
        
        metafile_content += "  <sizeinbytes>%d</sizeinbytes>\n" % size + \
        "  <included_files>\n" 
        
        for included_file_name in self.get_relative_file_paths():
            metafile_content += \
            "    <included_file_path>%s</included_file_path>\n" % included_file_name
            
        metafile_content += \
        "  </included_files>\n"
        
        if self.should_split:
            metafile_content += "  <splitfiles>\n"
            for split_file in self.get_splitted_archive_file():
                metafile_content += "    <split_file>\n"
                metafile_content += "      <filename>%s</filename>\n" % split_file.name
                metafile_content += "      <adler32sum>%s</adler32sum>\n" % split_file.get_adler32sum()
                metafile_content += "    </split_file>\n"
            metafile_content += "   </splitfiles>\n"

        elif not self.should_split:
            metafile_content += "  <adler32sum>%s</adler32sum>\n" % self.archive_file.get_adler32sum()
        metafile_content += "</archivemetainfo>\n\n"
        return metafile_content
        
    def create_par2_files(self):
        chunk_file_paths = self.get_archiving_file_paths()
        par2_cmd = [self.app.config.options["par2_bin_path"], "c", "-t+", os.path.join(self.arch_mssn.uploadcache_proj_folder.path, "%s.par2") % self.chunk_name ] 
        # Version to run for non-threaded par2 bin:
        #par2_cmd = [self.app.config.options["par2_bin_path"], "c", os.path.join(self.uploadcache_proj_folder.path, "%s.par2") % file_chunk.chunk_name ] 
        par2_cmd.extend(chunk_file_paths)
        self.log.info("About to create par2 files for chunk: %s in archmission %s" % (self.chunk_name, self.arch_mssn.id))
        OSUtils().exec_command(par2_cmd)
                