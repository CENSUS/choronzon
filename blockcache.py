'''
    blockcache.py provides a uniform API for Choronzon to
    store and correlate execution traces. It makes use of an
    external dependency/module called sortedcontainers.
'''

import sortedcontainers as sc

class BlockCache(object):
    '''
        Basic block cache implementation. It is based on a
        sorted dictionary.
    '''
    cache = None
    total = None


    def __init__(self):
        self.cache = sc.SortedDict()
        self.total = 0x0

    def yield_bbls(self):
        '''
            returns a generator for all basic blocks inside
            the cache.
        '''
        for start_ea, end_ea in self.cache.itervalues():
            yield (start_ea, end_ea)

    def get_count(self):
        '''
            Return the number of the basic block in this image
        '''
        return float(self.total)

    def add_bbl(self, key, value):
        '''
            Add a BBL with start address `key' and end address `value'
        '''
        if key == value[0]:
            self.total += 1
        self.cache[key] = value

    def get_bbl(self, bbl):
        '''
            Get a BLL (tuple with (startEA, endEA))
        '''
        return self.cache[bbl]

    def is_cached(self, bbl):
        '''
            aux: returns True if the bbl exists inside
            the block cache already.
        '''
        return bbl in self.cache

    def get_cached(self, bbl):
        '''
            if the bbl is cached then it retrieves the
            cached value, or in case it's not, it adds
            it to the cache and then returns the value.
        '''
        if self.is_cached(bbl):
            return self.get_bbl(bbl)

        bindex = self.cache.bisect(bbl)
        bstart = self.cache.iloc[bindex]
        left, right = self.get_bbl(bstart)
        if left < bbl and right > bbl:
            self.add_bbl(bbl, (left, right))
            return (left, right)
        else:
            return None

    @classmethod
    def parse_idmp(cls, idmp_iterable):
        '''
            parse the output of the disassembler module.
        '''
        mode = None
        cache = cls()

        for line in idmp_iterable:
            if '#' in line:
                if '#IMAGE#' in line:
                    mode = 'image'
                elif '#FUNCTIONS#' in line:
                    mode = 'functions'
                elif '#BBLS#' in line:
                    mode = 'bbls'
            elif mode == 'image':
                pass
            elif mode == 'functions':
                pass
            elif mode == 'bbls':
                start, end, _ = line.split(',')
                start = int(start, 16)
                end = int(end, 16)
                cache.add_bbl(start, (start, end))

        return cache
