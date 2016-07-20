import os
import importlib
import string
import chromosome
import configuration
import campaign

class Factory(object):
    '''
        Factory class generates chromosomes using user-defined
        parsers specified in the configuration.
    '''

    directory = None
    configuration = None
    serializer = None
    deserializer = None

    def __init__(self, seeddir):
        self.configuration = configuration.Configuration()
        self.campaign = campaign.Campaign()
        if seeddir != None:
            self.directory = self._check_path(seeddir)
        self._load_parser()


    def _check_path(self, path):
        '''
            aux: checks if a file or directory exists and
            returns the absolute path.
        '''
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise IOError('Seed directory "%s" does not exist' % path)
        return path

    def _load_parser(self):
        '''
            attempt to load the module and the appropriate classes
            according to the "Parser" configuration setting.
        '''
        if not self.configuration or self.configuration == None:
            raise configuration.ConfigurationError(
                    'Configuration is not loaded'
                    )
        self.parser = importlib.import_module(
                'chromosome.parsers.%s' % self.configuration['Parser']
                )
        self.serializer = getattr(
                self.parser,
                '%sSerializer' % self.configuration['Parser']
                )
        self.deserializer = getattr(
                self.parser,
                '%sDeserializer' % self.configuration['Parser']
                )

    def _generate_chromosome(self, fname):
        '''
            It parses the current filename, and then append
            the genes that found in a chromosome and return it.
        '''
        chromo = chromosome.Chromosome(
                    serializer=self.serializer,
                    deserializer=self.deserializer
                )
        if fname != None:
            print '[!] Parsing: %s (%s)' % (fname, chromo.uid)
            self.campaign.log('Parsing: %s (%s)' % (fname, chromo.uid))
            chromo.deserialize(fname)
        return chromo

    def generate(self):
        '''
            This is a generator that yields chromosomes,
            that represent each file in the chosen path.
        '''
        for root, _, files in os.walk(self.directory):
            for fname in files:
                yield self._generate_chromosome(
                        os.path.join(root, fname)
                        )

    @classmethod
    def build_empty(klass):
        obj = klass(None)
        return obj._generate_chromosome(None)

    @classmethod
    def build(cls, seed_dir):
        '''
            aux: automate the process of parsing seed files.
        '''
        o = cls(seed_dir)
        return o.generate()
