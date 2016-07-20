#!/usr/bin/env python
import sys
import os
import argparse

import world
import chromosome
import fuzzers.strategy as strategy
import configuration
import campaign
import tracer
import evaluator


class Choronzon(object):
    '''
        https://en.wikipedia.org/wiki/Choronzon
    '''
    configuration = None
    campaign = None
    population = None
    strategy = None
    tracer = None
    evaluator = None

    def __init__(self, configfile=None):
        '''
            Initialization method of Choronzon. Reads the configuration,
            instantiates objects of the vital classes, builds and
            analyzes the first generation of chromosomes by reading
            the initial population provided to the fuzzer.
        '''
        # configuration is a singleton
        self.configuration = configuration.Configuration(configfile)
        self.campaign = campaign.Campaign(self.configuration['CampaignName'])

        seedpath = self.campaign.copy_directory(
                self.configuration['InitialPopulation'], name='seedfiles')

        self.tracer = tracer.Tracer()
        self.strategy = strategy.FuzzingStrategy()
        self.population = world.Population(self.tracer.cache)
        self.evaluator = evaluator.Evaluator(self.tracer.cache)

        try:
            self.sharedpath = self.campaign.create_shared_directory(
                    self.configuration['ChromosomeShared'])
        except:
            self.sharedpath = None

        # Initialize factory for building chromosome
        # and the proxy for computing the fitness.
        chromosomes = chromosome.Factory.build(seedpath)
        for chromo in chromosomes:
            self.population.add_chromosome(chromo)

        self.analyze()

    def _grab_from_shared(self):
        '''
            This functions is looking for files in the shared directory. If a
            file has not already been processed, it uses it to build a new
            Chromosome and import it into the current population.
        '''
        listed_files = os.listdir(self.sharedpath)

        for curr in listed_files:
            if not self.campaign.already_processed(curr):
                abspath = self.campaign.copy_from_shared(curr)
                # build an empty chromosome, which will be filled with the
                # contents of the file from the shared directory
                new_chromo = chromosome.Factory.build_empty()
                new_chromo.load_chromosome(abspath)
                self.population.add_chromosome(new_chromo)
                # this is for updating the generation trace
                self.population.add_trace(new_chromo.uid, new_chromo.trace)

    def fuzz(self):
        '''
            Each time fuzz method is called, it is indicating that a new epoch
            has begun. The function picks random couples of chromosomes from the
            population and apply to them recombination and mutation algorithms.
            Finally, the new (fuzzed) chromosomes are imported to the new
            generation.
        '''
        self.population.new_epoch()
        self.campaign.log('Fuzzing of chromosomes has begun.')

        # This is to keep the family tree of the chromosomes
        for male, female in self.population.get_couple_from_previous(True):
            # assume that the UID is colliding with another's chromosome UID
            uid_collision = True

            maleclone = male.clone()
            femaleclone = female.clone()

            # assign new UIDs to the new chromosomes until they are unique
            while uid_collision:
                if self.population.does_exist(maleclone.uid) == False and \
                        self.population.does_exist(femaleclone.uid) == False:
                    uid_collision = False
                else:
                    maleclone.new_uid()
                    femaleclone.new_uid()

            son, daughter = self.strategy.recombine(maleclone, femaleclone)

            self.population.add_chromosome(son)
            self.population.add_chromosome(daughter)

        self.campaign.log('The stage of fuzzing is finished')

        if 'KeepGenerations' in self.configuration and \
                self.configuration['KeepGenerations']:
            gpath = self.campaign.create_directory(
                    '%s' % self.population.epoch
                    )
            for chromo in self.population.get_all_from_current():
                path = os.path.join(
                            '%s' % gpath,
                            '%s' % chromo.uid
                            )
                with open(path, 'wb') as fout:
                    fout.write(chromo.serialize())

    def evaluate_fuzzers(self):
        '''
            assigns credits to the combinations of mutators and recombinators
            that have generated elite chromosomes (they have survived through
            the elitism step to the next generation). For every such chromosome,
            the pair is more likely to be chosen based on the lottery selector.
        '''

        involved = {}

        # for every derived chromosome (it has a fuzzer) assign it a fuzzer
        # score of 0. This step only considers chromosomes that have been
        # involved in this fuzzing cycle.
        for chromo in self.population.get_all_from_previous():
            if chromo.fuzzer == None:
                continue
            if chromo.fuzzer not in involved:
                involved[chromo.fuzzer] = 0

        # for every chromosome that is involved (has been generated in this
        # step) and has survived, increase its fuzzer's score by one
        for chromo in self.population.get_all_from_current():
            if chromo.fuzzer == None:
                continue
            if chromo.fuzzer not in involved:
                involved[chromo.fuzzer] = 0
            else:
                involved[chromo.fuzzer] += 1

        # update the strategy instance with the new fuzzer scores, so that
        # the mutator/combinator pair is more likely to be chosen again
        for fuzzer, score in involved.iteritems():
            if score > 0:
                self.strategy.good(fuzzer, score)

            # not sure if negative feedback will help, so ignore
            # for now
            #else:
            #    self.strategy.bad(fuzzer)

    def analyze(self):
        '''
            Analyze the corpus of the current generation, by instrumenting the
            execution using the Tracer class.
        '''

        self.campaign.log('Analysis of chromosomes.')
        self.campaign.log('Current generation has %d chromosomes.' % (
                len(self.population.current))
            )
        crashed_uids = []

        for chromo in self.population.get_all_from_current():
            newfile = self.campaign.create(
                                    '%s' % chromo.uid,
                                    chromo.serialize()
                                    )
            self.campaign.log('Analyzing %s' % chromo.uid)
            trace = self.tracer.analyze('%s' % chromo.uid)
            self.campaign.log('Analysis of %s finished' % chromo.uid)

            # if the fuzzed file triggered a bug (yay!!), remove it from the
            # population, since it may trigger the same bug again and again
            if trace.has_crashed:
                crash_dir = self.campaign.create_directory('crashes')
                path = os.path.join(crash_dir, '%s' % chromo.uid)
                with open(path, 'wb') as fout:
                    fout.write(chromo.serialize())
                self.campaign.log('CRASH! :)')
                self.campaign.log('The trigger file is saved at %s.' % path)
                crashed_uids.append(chromo.uid)
            else:
                self.population.add_trace(chromo.uid, trace)
                try:
                    os.unlink(newfile)
                except:
                    # Sometimes newfile is still used by the OS and unlink
                    # raises an exception. We just ignore this.
                    pass

        # Erase of chromosomes must be done after iterating the current
        # generation. Otherwise, python will raise a RuntimeError expcetion.
        for uid in crashed_uids:
            self.population.delete_chromosome(uid)

        if self.sharedpath != None:
            self._grab_from_shared()

        self.campaign.log('Evaluation stage of chromosomes has begun')
        self.evaluator.evaluate(self.population)

        # new epoch will be created in elitism function
        self.population.elitism()
        self.campaign.log('Elite generation contains %d chromosomes.' % (
                len(self.population.current)
            ))

        if len(self.population.current) < 2:
            raise ValueError('Elitism resulted to just one chromosome.'\
                    'Usually this is due to bad initial corpus (limited ' \
                    'seedfiles provided or they are identical) or there is a '\
                    'problem with the instrumented binary. For example, '\
                    'maybe the basic blocks that are visited in every run are '\
                    'the same.')
        self.evaluate_fuzzers()

        # if there are multiple instances of choronzon, dump the chromosomes
        # from the elite generation to the shared directory.
        if self.sharedpath != None:
            for chromo in self.population.get_all_from_current():
                filename = str(chromo.uid)
                if not self.campaign.already_processed(filename):
                    self.campaign.dump_to_shared(filename,
                                        chromo.dumps_chromosome())

        elite_dir = self.campaign.create_directory('%s' % self.population.epoch)

        if 'KeepGenerations' in self.configuration \
                            and self.configuration['KeepGenerations']:
            for chromo in self.population.get_all_from_current():
                path = os.path.join(elite_dir, '%s' % chromo.uid)
                with open(path, 'wb') as fout:
                    fout.write(chromo.serialize())

    def start(self):
        while True:
            self.fuzz()
            self.analyze()

    def stop(self):
        print '[+] Bye! :)'

def main(args):
    print '[+] Choronzon fuzzer v.0.1'
    print '[+] starting campaign...'

    choronzon = Choronzon(args.config)

    try:
        choronzon.start()
    except KeyboardInterrupt:
        choronzon.stop()

    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description='Choronzon v0.1\nAn evolutionary knowledge-based fuzzer'
            )
    parser.add_argument(
            'config',
            help='/path/to/config/file.py'
            )
    arguments = parser.parse_args()
    sys.exit(main(arguments))
