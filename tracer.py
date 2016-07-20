#!/usr/bin/env python

import os
import struct
import sortedcontainers as sc
import settings

import campaign
import disassembler
import analyzer
import configuration
import blockcache as bcache

class Trace(object):
    images = None
    # bbls_per_image = None
    set_per_image = None
    functions = None
    trace = None
    total = None
    has_crashed = None

    def __init__(self):
        self.has_crashed = False
        self.images = []
        self.total = 0x0
        #self.bbls_per_image = {}
        self.set_per_image = {}

    def add_image(self, image):
        '''
            Adds a new image name into the trace.
        '''
        self.images.append(image)
        #self.bbls_per_image[image] = []
        self.set_per_image[image] = sc.SortedSet()

    def add_bbl(self, image, bbl):
        '''
            Adds a new basic block into the trace.
        '''
        # The bbl given as input in this function is
        # taken from the block cache. Technically, this means
        # that it corresponds to the basic blocks of IDA.
        #self.bbls_per_image[image].append(bbl)
        self.set_per_image[image].add(bbl)
        self.total += 1

    def get_total(self):
        '''
            Returns the total number of basic blocks in the trace.
        '''
        return self.total

    def get_unique_total(self):
        '''
            Returns the total number of unique basic blocks
            of all images, hit by the current trace.
        '''
        count = 0x0
        for img in self.set_per_image:
            count += len(self.set_per_image[img])
        return count

    def get_difference_per_image(self, trace):
        '''
            This function yields a tuple with the image name
            and the difference between this trace object
            and the trace object given as argument.
        '''
        assert len(self.set_per_image) == len(trace.set_per_image)
        for img in self.images:
            this = self.set_per_image[img]
            other = trace.set_per_image[img]
            yield img, this - other

    def get_similarity(self, trace):
        '''
            Returns the percentage of similar basic block between two traces.
            If the return value is 1.0, the traces are equal. On the other hand,
            if it is 0.0, the traces have not any common basic block.
        '''
        assert len(self.set_per_image) == len(trace.set_per_image)
        faults = 0x0
        for img in self.images:
            this = self.set_per_image[img]
            other = trace.set_per_image[img]
            faults += len(this - other)
        return faults / float(self.get_unique_total())

    def update(self, trace):
        '''
            Updates the trace.
        '''
        for img in trace.images:
            if img not in self.images:
                self.add_image(img)
            self.set_per_image[img].update(trace.set_per_image[img])
            self.total += trace.total

class Tracer(object):
    cache = None
    campaign = None
    analyzer = None
    disassembler = None
    configuration = None

    def __init__(self, configfile=None):
        self.cache = {}

        print '[+] Loading configuration...'
        self.configuration = configuration.Configuration(configfile)

        print '[+] Loading Disassembler module...'
        self.disassembler = getattr(
                    disassembler,
                    self.configuration['Disassembler']
                )(self.configuration['DisassemblerPath'])

        print '[+] Loading Analyzer module...'
        if 'Timeout' not in self.configuration:
            timeout = 20
        else:
            timeout = self.configuration['Timeout']
        self.analyzer = analyzer.Coverage(settings.pintool, timeout)

        self.initialize_campaign()
        print '[+] Tracer module is initialized.'

    def initialize_campaign(self):
        '''
            Initiliaze a new tracer campaign.
        '''
        print '[+] Initializing campaign...'
        self.campaign = campaign.Campaign(
            self.configuration['CampaignName']
            )

        print '[+] Parsing whitelist...'
        for target in self.configuration['Whitelist']:
            exe = self.campaign.add(target)
            print '    [-] Disassemblying %s...' % (os.path.basename(exe))
            self.disassemble(exe)

    def disassemble(self, exe):
        '''
            Disassembles the binary and imports the basic block
            that has was found into the BlockCache.
        '''
        # dump the disassembly
        dmp = self.disassembler.disassemble(
                    exe,
                    output=self.campaign.campaign_dir
                )

        self.cache[os.path.basename(exe)] = bcache.BlockCache.parse_idmp(dmp)

    def parse_trace_file(self, trace_file):
        '''
            Parses the format of the trace file (actually a named pipe).

            The format of the trace file is the following:
            [number of images, 1 byte ]
            IMAGE SECTION
            [
               [image name length,  2 bytes]
               [image name, variable length]
               ...
            ]
            BASIC BLOCK SECTION
            [
               [image number,       8 bytes]
               [basic block offset, 8 bytes]
               ...
            ]

            Note that image section must be prior to basic block section.
            If the image number attribute, in a chunk which is contained
            in the basic block section, is 0xffffffffffffffff, then a
            signal (in Linux) or an exception (in Windows) has been
            raised in the monitored application.
        '''
        trace = Trace()
        nimg = 0x0
        with open(trace_file, 'rb') as fin:
            nimg = ord(fin.read(1))
            # read the image section
            for _ in xrange(nimg):
                imgname_sz, = struct.unpack('<H', fin.read(2))
                image_name = fin.read(imgname_sz)
                trace.add_image(os.path.basename(image_name))
            # read the basic block section
            buf = fin.read(16)
            while buf:
                ino, bbl = struct.unpack('<QQ', buf)
                if ino == 0xffffffffffffffffL:
                    if bbl != 0xC:
                        trace.has_crashed = True
                else:
                    bbl = self.cache[trace.images[ino]].get_cached(bbl)
                    if bbl != None:
                        trace.add_bbl(trace.images[ino], bbl)
                buf = fin.read(16)

        self.campaign.delete_pipe(trace_file)
        return trace

    def analyze(self, seedid):
        '''
            Grabs a seed from the corpus, executes the application using
            the analyzer module and returns the trace.
        '''
        path = self.campaign.get(seedid)
        output = self.campaign.create_pipe('%s.dmp' % seedid)
        cmd = self.configuration['Command'] % path
        os.chdir(self.campaign.campaign_dir)
        dmp = self.analyzer.run(execmd=cmd, output=output,
                                whitelist=self.configuration['Whitelist'])
        return self.parse_trace_file(dmp)

