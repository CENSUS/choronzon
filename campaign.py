#!/usr/bin/env python

import os
import time
import shutil
import random
import platform

class Singleton(type):
    '''
        Assing this class as the __metaclass__ member of a class and it will
        convert it to a singleton class.
    '''
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(Singleton, cls).__call__(*args, **kwargs)
            return cls.__instance


class Campaign(object):
    '''
        A singleton class for managing files and directories in a campaign.
    '''
    __metaclass__ = Singleton
    campaign_id = None
    work_dir = None
    temp_dir = None
    local_dir = None
    shared_dir = None
    campaign_dir = None
    files = None
    shared_files = None
    chromo_files = None

    def __init__(self, campaign_id=None, work_dir='.'):
        if self.campaign_id == None:
            self.files = []
            self.shared_files = []
            self.chromo_files = {}
            self.work_dir = self.__checkfilename(work_dir)
            self.new_campaign(campaign_id)

    def log(self, msg):
        self.logfp.write('%s\n' % msg)
        self.logfp.flush()

    def copy_directory(self, input_path, name=None):
        '''
            Takes as input a list or tuple with the absolute path names
            of the initial seed files and copies them at a special directory
            named `seedfiles' in the campaign directory
        '''
        if not name or name == None:
            name = os.path.basename(input_path)

        path = self.create_directory(name)
        for filename in os.listdir(input_path):
            name = os.path.join(input_path, filename)
            with open(name, 'rb') as fin:
                with open(os.path.join(path, filename), 'wb') as fout:
                    fout.write(fin.read())
        return path

    def __checkfilename(self, directory):
        '''
            aux: raises exception if the filename does not exist or returns
            the absolute filepath.
        '''
        if not os.path.exists(directory):
            raise IOError(
                'File "%s" does not exist'
                % directory
                )
        return os.path.abspath(directory)

    def new_id(self):
        '''
            crafts an unique id for a campaign by combining a timestamp
            and a random number.
        '''
        newid = random.random().as_integer_ratio()[0]
        newid += time.time().as_integer_ratio()[1]
        return 'campaign-%d' % newid

    def new_campaign(self, campaign_id=None):
        '''
            creates a new directory for the new campaign. The name of the
            directory is the new campaign id.
        '''
        if campaign_id and campaign_id != None:
            self.campaign_id = campaign_id
        else:
            self.campaign_id = self.new_id()

        self.campaign_dir = os.path.join(self.work_dir, self.campaign_id)
        self.temp_dir = self.create_directory('.tmp')
        self.local_dir = self.create_directory('.local')
        self.chromo_dir = self.create_directory('.chromo')
        self.logfp = open(os.path.join(self.campaign_dir, 'log.txt'), 'a')
        self.log('Log opened for writing at %s' % time.ctime())

    def get_chromosome(self, uid):
        '''
            returns the full path of the chromosome file inside the
            campaign directory.
        '''
        if uid not in self.chromo_files:
            raise KeyError('Could not find chromosome: %s' % uid)

        return self.chromo_files[uid]

    def add_chromosome(self, uid, data):
        '''
            inserts a chromosome in the chromosome directory and it
            updates the path to the file.
        '''
        path = os.path.join(self.chromo_dir, '%s' % uid)
        path = os.path.abspath(path)
        with open(path, 'wb') as fout:
            fout.write(data)
        self.chromo_files[uid] = path
        return path

    def delete_chromosome(self, uid):
        '''
            removes the given uid from the dictionary of the chromo
            files as well as the file it points to.
        '''
        if uid not in self.chromo_files:
            raise KeyError('Could not find chromosome: %s' % uid)

        os.remove(self.chromo_files[uid])
        del self.chromo_files[uid]

    def cleanup(self):
        '''
            deletes the campaign directory.
        '''
        shutil.rmtree(self.campaign_dir)

    def copy_to_campaign(self, filename):
        '''
            aux: copies the filename to the campaign_dir directory.
        '''
        name = os.path.basename(filename)
        with open(filename, 'rb') as fin:
            newpath = os.path.join(
                    self.campaign_dir,
                    name
                    )
            with open(newpath, 'wb') as fout:
                fout.write(fin.read())

    def create_shared_directory(self, abspath):
        '''
            A path to the shared directory that will be used for communicating
            with other Choronzon's instances. If the directory does not exist,
            it will create it.
        '''
        self.shared_files = []
        if not os.path.exists(abspath):
            os.makedirs(abspath)
        self.shared_dir = abspath
        return abspath

    def create_directory(self, path):
        '''
            Creates a directory (if it does not already exists)
            and returns its path.
        '''
        path = os.path.join(self.campaign_dir, path)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def delete_pipe(self, pipe_name):
        '''
            Deletes a named pipe.
        '''
        if platform.system() == 'Linux':
            try:
                os.unlink(pipe_name)
            except OSError as oserr:
                print '[!] ERROR: Could not delete pipe:', oserr

        elif platform.system() == 'Windows':
            # Windows delete automatically the pipe when all handles to it
            # are closed. So there's nothing to delete.
            pass

    def create_pipe(self, seedid):
        '''
            This function crafts a valid name of a named pipe depending on the
            underlying operating system.
        '''
        name = None
        if platform.system() == 'Linux':
            pipe_absname = os.path.join(self.temp_dir, 'pipe%s' % seedid)
            while os.path.exists(pipe_absname):
                pipe_absname = os.path.join(self.temp_dir,
                                'pipe%s' % str(random.randint(0, 0xFFFFFFFF)))
            name = pipe_absname
        elif platform.system() == 'Windows':
            # name = '\\\\.\\pipe%s' % seedid
            name = 'pipe%s' % seedid
            # should check here, if the pipe already exists.
            # however, windows automatically delete the pipe if there isn't
            # any open handle to it. So, theoritically there's no prob here.
        return name

    def create(self, filename, data=None):
        '''
            create a new file inside the temporary directory.
            if data is defined, write the data into the new file.
        '''
        if filename in self.files:
            raise ValueError(
                'File "%s" already exists.'
                % filename
                )
        name = os.path.basename(filename)
        self.files.append(name)
        filepath = self.get(name)
        if data != None:
            with open(
                    filepath,
                    'wb'
                    ) as fout:
                fout.write(data)

        return filepath

    def copy_from_shared(self, filename):
        '''
            Copies a pickled file (usually a pickled chromosome object) from the
            shared directory, to a local directory inside the campaign. Notice
            that, if a file with the same name was copied previously, then it
            does nothing.
        '''
        if not self.already_processed(filename):
            self.shared_files.append(filename)
            with open(os.path.join(self.shared_dir, filename), 'r') as fin:
                with open(os.path.join(self.local_dir, filename), 'wb') as fout:
                    fout.write(fin.read())
        return os.path.join(self.local_dir, filename)

    def already_processed(self, filename):
        '''
            Returns True if this fuzzer has already processed this specific
            chromosome pointed by `filename'. Process could mean, that either
            this instance of the fuzzer dumped the chromosome in the shared
            directory or the chromosome was imported from the shared directory.
        '''
        return filename in self.shared_files

    def dump_to_shared(self, filename, bytestring):
        '''
            Dumps a bytestring into the shared directory and into a local
            directory.
        '''
        if filename not in self.shared_files:
            self.shared_files.append(filename)
            path = os.path.join(self.shared_dir, filename)
            localpath = os.path.join(self.local_dir, filename)
            with open(path, 'wb') as fout:
                fout.write(bytestring)
            with open(localpath, 'wb') as fout:
                fout.write(bytestring)

    def get(self, filename):
        '''
            retrieve a file already add()ed in the campaign.
        '''
        if filename not in self.files:
            raise IndexError(
                'File "%s" was not found'
                % filename
                )
        return os.path.join(
            self.campaign_dir,
            filename
            )

    def add_to(self, out, inp):
        '''
            Copies `filename' to `fullpath' directory.
        '''
        outfull = os.path.join(out, os.path.basename(inp))
        with open(inp) as fin:
            with open(outfull, 'wb') as fout:
                fout.write(fin.read())
        return outfull

    def add(self, filename):
        '''
            copy a file inside the campaign directory.
        '''
        name = os.path.basename(filename)
        if name not in self.files:
            self.copy_to_campaign(filename)
            self.files.append(name)
        return self.get(name)

