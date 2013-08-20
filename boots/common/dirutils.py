'''
Created on 08-Feb-2013

@author: anand

A set of methods to assist with folders and validation of folders
'''
import logging
from os.path import abspath, getmtime, splitext, dirname, exists, join, isdir
from fnmatch import fnmatch
import os
import zipfile
import re
import tempfile

# since we are a library, let's add null handler to root to allow us logging
# without getting warnings about no handlers specified
logging.getLogger().addHandler(logging.NullHandler())

class DirUtils(object):
    
    def is_updated(self, file_path, timestamp):
        '''
        Checks if file_path's modified time is newer than timestamp
        :param str file_path: str containing the file_path (absolute or relative to current working dir) 
        :type float timestamp: str or float containing the timestamp against which the file is to be checked
        :returns: boolean. TypeError if timestamp cannot be converted to float. OSError if file does not exist 
        '''
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
        return getmtime(file_path) > timestamp
    
    def read_file(self, source, max_size):
        '''
        Read the file specified by the source having size less than max_size specified and returns the byte code.
        :param str or File-like object source: A File-like object or a name of a file 
        :param int max_size: The max size of the file to be read. If max-size is None, read the whole file
        :returns: bytes
        '''
        if hasattr(source, 'read'): # if file-like object, read from it.
            return source.read() if max_size == None else source.read(max_size)   
        with open(source, 'rb') as fp: # opening in binary mode
            return fp.read() if max_size == None else fp.read(max_size) 
        
    def get_zip_name(self, filename):
        '''
        Returns a zip name based of filename. e.g. a/b/c.pr returns a/b/c.zip   
        :param str filename: Filename whos zipname is to be returned
        :returns: zipfilename (e.g. a/b/c.pr returns a/b/c.zip, a/b/c returns a/b/c.zip)
        '''
        base, _ = splitext(filename)
        return base + '.zip'

    def get_dir_name(self, source):
        '''
        Returns the directory component of a pathname
        :param str source: Path whose dir name is to be returned
        :returns: str
        '''
        return dirname(source)
    
    def  make_zip(self, path, name, glob='*', regexp=None, recursive=False):
        ''' 
         Creates a zip file and populates with files that match either glob (shell filename pattern) or regular expression.
        :param str path: The path where the zip is to be created.
        :param str name: The name of the zip file to be created.
        :param str glob: Pattern for file matching (within path)
        :param str regexp: regular Expression for file matching
        :param bool recursive: Determines whether the method traverses path recursively or not.
        :returns: Path to the generated zip file
        '''
        
        zipfilename = os.path.join(path, name)      #TODO:The zip files should lie in some other folder.
        
        if os.path.exists(zipfilename):
            os.remove(zipfilename)
                
        files = self.get_files(path, glob=glob, regexp=regexp, recursive=recursive)
        with zipfile.ZipFile(zipfilename, mode="w") as zipf:
            [ map(lambda x: zipf.write(os.path.join(path, x), arcname=x), fl) for fl in [ map(lambda x: os.path.join(dirname, x), flist) for dirname, flist in files ]]
        return zipfilename
    
    def make_relative(self, base_path, path, user=None):
        '''
         Returns the relative portion of the path relative to base_path
        :param str base_path: The base from where the relative path is to be calculated.
        :param str path: The path to which the relative path is to be calculated.
        :param str user: Username of the user that is currently logged in can be retrived by bottle.request.environ
        :returns: str
        '''
        base_path = self.resolve_path(base_dir=base_path, path='.', user=user)
        subpath = os.path.relpath(path, base_path)
        if os.sep != '/':
            subpath = subpath.replace(os.sep, '/')
        return subpath
    
    def validate_dir(self, base_dir,  path=".", sub_dir=None, check_exists=True):
        ''' 
        Returns True if path is a valid directory, else raises ValueError
        dir has to be a subdir base_dir or base_dir/sub_dir if sub_dir is not None
        :param str base_dir: The base directory.
        :param str path: The relative path.
        :param str sub_dir: An optional sub_dir which is appended to base_dir to create a chroot
        :param bool check_exists: Also checks if the path really exists or not
        :returns: bool
        '''
        newpath = self.resolve_path(base_dir, path, sub_dir)
        if  check_exists:
            if not exists(newpath) or not isdir(newpath):
                raise ValueError('{} is not a valid directory'.format(path))
        return True

    def resolve_path(self, base_dir, path, sub_dir=None):
        ''' 
        Converts relative directory to a more complete path (either absolute or relative) based of base directory. Validates that the
        path resides within base_dir. An option sub_dir, if provided, is added to base_dir. 
        The purpose of this is to mimic a chroot and ensure that the given path exists completely within the chroot of (base_dir/sub_dir).
        In other words, by relative addressing such as path = ../../../xyz, a request to unauthorized areas cannot be made
        :param str base_dir - The base directory for all operations.
        :param str path - the path obtained from the client. May be an absolute path
        :param str sub_dir: An optional sub_dir which is appended to base_dir to create a chroot
        :returns: Complete resolved path as str
        '''
        absprefix = abspath(join(base_dir, sub_dir)) if sub_dir is not None else abspath(base_dir)
        newpath = abspath(join(absprefix, path))
        if not newpath.startswith(absprefix):
            raise ValueError('path parameter '+path+' invalid.' + ' base = ' + absprefix + ' newpath = ' + newpath)
        return newpath
                    
    def get_files(self, path, glob='*', regexp=None, recursive=False):
        '''
         Gets files that match either glob (shell filename pattern) or regular expression. 
        
        :param str path: The path from where the files are to be fetched.
        :param str glob: Pattern for file matching
        :param str regexp: regular Expression for file matching
        :param bool recursive: determines whether the method traverses path recursively or not
        :returns: List of files as List of str
        '''
        self.validate_dir(base_dir=path, path='.') # check if this is a valid/accessible dir within the base_dir (i.e path) 
        files = list(os.walk(path)) if recursive else [next(os.walk(path, topdown=True))]
        if regexp == None:
            files = [(x[len(path)+1:].replace('\\', '/'), list(filter(lambda f: fnmatch(f, glob), z))) for x, _, z in files]
        else:
            prog = re.compile(regexp)
            files = [(x[len(path)+1:].replace('\\', '/'), list(filter(lambda f: prog.match(f), z))) for x, _, z in files]
            
        files = list(filter(lambda x: x[1] != [], files))
        return files
    
    def make_dir(self, abspath, mode=0o770):
        '''
         Creates a dir if none exists. Does nothing if a directory exists. First checks if path is valid
        returns True on success. Raises error cannot be created. ValueError is it is an invalid (or restricted) path
        
        :param abspath: The path to the directory to be created,should be the fully qualified path
        @type abspath: str
        
        :param mode: Permissions of the folder
        @type mode: oct
        
        :returns: bool
        '''
        self.validate_dir(base_dir=abspath, check_exists=False)
        
        if exists(abspath) and isdir(abspath):
            return True
        
        os.makedirs(abspath, mode)
        return True
    
    def make_temp_dir(self, path, sub_dir=None, prefix=''):
        '''
         Creates a temp directory in the specified path
        
        :param path: The path to where the temp dir is to be created.
        @type path: str
        
        :param user: Username of the user that is currently logged in can be retrived by bottle.request.environ
        @type user: str
        
        :param prefix: The prefix to be attached to the temp dir.
        @type prefix: str
        
        :returns: The complete path to the new dir as str
        '''
        
        base_path = self.resolve_path(base_dir=path, path='.', sub_dir=sub_dir)
        self.make_dir(base_path)
        new_path = tempfile.mkdtemp(prefix=prefix, dir=base_path)
        self.validate_dir(new_path, check_exists=True) 
        return new_path
    
    def file_write(self, abspath, filename, fp, mode="wb"):
        '''
         Write a file available in a filelike object.
        
        :param abspath: absolute path
        @type abspath: str
        
        :param filename: name of the file
        @type filename: str
        
        :param fp: file-like object which has the data to be written
        @type fp: file pointer
        
        :param mode: mode to open the target file in
        @type param_mode: str
        '''
        max_read=100*1024
        os.umask(0o007)
        with open(os.path.join(abspath, filename), mode) as fout:
            byts = fp.read(max_read)
            while byts not in [ b'', '']: 
                fout.write(byts)
                byts = fp.read(max_read)
                
    
    def get_source_prefix(self, filename):
        '''
         Returns the name of any given file without the extension.
        
        :param filename: Name of the file.
        @type filename: str
        
        :returns: str 
        '''
        fname = os.path.basename(filename)
        return os.path.splitext(fname)[0]


if __name__ == '__main__':
    pass