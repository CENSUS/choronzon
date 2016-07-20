'''
    This module contains classes that handle each generation and the whole
    population.
'''
import random
import tracer

import campaign
import chromosome

class NaiveSelector(object):
    '''
        NaiveSelector is initialized with a list of chromosome identification.
        It is responsible to return randomly a chromosome. When all chromosomes
        has been selected at least once, is_done() returns True.
    '''
    def unfair_coinflip(self, prob=0):
        '''
            Returns True with probability 1/`prob'.
        '''
        rndval = random.randint(0, prob)

        if rndval == prob:
            return True
        else:
            return False

    def __init__(self, whatever, initial=0):
        # key is the identification of a chromosome
        # value is the number of the times that has been selected.
        self.objdict = dict(map(lambda filename: (filename, initial), whatever))

    def is_done(self):
        '''
            Returns True if all chromosomes has been selected at least once.
        '''
        done = True
        if 0 in self.objdict.values():
            done = False
        return done

    def select(self):
        '''
            Selects a chromosome and returns its identification.
            The probability for selecting a chromosome is inversely proportional
            to the times that it already had been selected.
        '''
        done = False

        while not done:
            objkey = random.choice(self.objdict.keys())
            done = self.unfair_coinflip(self.objdict[objkey])

        self.objdict[objkey] += 1

        return objkey


class Generation(object):
    '''
        A Generation object holds the chromosomes along with the metrics
        collected so far.
    '''
    epoch = None
    trace = None
    max_metrics = None
    min_metrics = None
    chromosomes = None
    selector = None
    campaign = None

    def __init__(self, epoch=0):
        self.campaign = campaign.Campaign()

        self.epoch = epoch
        # This is a dictionary with key uid and value the chromosome object
        self.chromosomes = dict()
        self.selector = None
        self.trace = tracer.Trace()
        self.max_metrics = dict()
        self.min_metrics = dict()

    def __iter__(self):
        for key in self.chromosomes:
            yield self.get_chromosome(key)

    def __getitem__(self, uid):
        '''
            Returns the requested chromosome.
        '''
        return self.get_chromosome(uid)

    def __setitem__(self, uid, value):
        '''
            Adds a chromosome in the current generation.
        '''
        self.set_chromosome(uid, value)

    def __contains__(self, item):
        return item in self.chromosomes

    def set_chromosome(self, uid, chromo):
        '''
            adds the chromosome to the dictionary of chromosomes
            as well as stores the pickled chromsome object inside the
            campaign.
        '''
        path = self.campaign.add_chromosome(
                chromo.uid,
                chromo.dumps_chromosome()
                )

        self.chromosomes[uid] = path
        return path

    def get_chromosome(self, uid):
        '''
            instantiates the factory class in order to build a new
            and empty chromosome which is then loaded from a saved
            pickle object inside the campaign. The new chromosome is
            returned.
        '''
        empty = chromosome.Factory.build_empty()
        empty.load_chromosome(self.campaign.get_chromosome(uid))
        return empty

    def delete_chromosome(self, uid):
        '''
            delete the chromsome corresponding to the given uid from
            any list or dictionary as well as the file from the disk.
        '''
        chromo = self.get_chromosome(uid)
        self.campaign.delete_chromosome(uid)
        del self.chromosomes[uid]
        return chromo

    def delete(self, uid):
        '''
            Deletes a chromosome from the current generation.
        '''
        return self.delete_chromosome(uid)

    def __len__(self):
        '''
            Returns the number of the chromosomes in the current generation.
        '''
        return len(self.chromosomes)

    def get_all(self):
        '''
            Yields all the chromosomes included in this generation.
        '''
        for uid in self.chromosomes:
            yield self.get_chromosome(uid)

    def select(self):
        '''
            Selects randomly a chromosome using the selector class that
            has been assigned to the current generation. When the selector
            is finished, it returns None.
        '''
        try:
            if self.selector.is_done():
                return None
        except AttributeError:
            self.selector = NaiveSelector(
                    self.chromosomes.keys()
                    )

        return self.get_chromosome(self.selector.select())

    def set_fitness(self, uid, fitness):
        '''
            Sets the fitness of a specific chromosome.
        '''
        chromo = self.get_chromosome(uid)
        chromo.fitness = fitness
        self.set_chromosome(chromo.uid, chromo)

    def clear_metrics(self):
        self.max_metrics = {}
        self.min_metrics = {}

    def set_metrics(self, uid, metrics):
        '''
            Sets the `metrics' to the chromosome corresponding to the
            given uid.
        '''

        chromo = self.get_chromosome(uid)
        chromo.set_metrics(metrics)
        self.set_chromosome(uid, chromo)

        for name in metrics:
            if name not in self.max_metrics \
                    or metrics[name] > self.max_metrics[name]:
                self.max_metrics[name] = metrics[name]

            if name not in self.min_metrics \
                    or metrics[name] < self.min_metrics[name]:
                self.min_metrics[name] = metrics[name]

    def extend(self, dct):
        '''
            Extends the chromosomes in the current generation.
        '''
        for uid, chromo in dct.iteritems():
            self.set_chromosome(uid, chromo)


class Population(object):
    '''
        Population constists of two generations. Normally, one that contains
        the elite generation and another one with the fuzzed seed files. Also,
        this class has operation about messing with the chromosomes of those
        two generation. Using the API, you're able to retrieve/delete/add
        chromosomes.
    '''
    epoch = None
    previous = None
    current = None

    def __init__(self, cache, epoch=0):
        self.cache = cache
        self.epoch = epoch
        self.previous = None
        self.current = Generation(self.epoch)

        # Setup image leaders and basic blocks leaders
        self.image_leaders = {}

        for image_name in self.cache:
            self.image_leaders[image_name] = {}
            bbl_leaders = {}
            for startea in self.cache[image_name].yield_bbls():
                bbl_leaders[startea] = None
            self.image_leaders[image_name] = bbl_leaders

    def get_chromo_from_current(self, uid):
        '''
            Returns a chromosome from the current generation which has uid
            equal to `uid'. If there isn't such chromosome, returns None.
        '''
        try:
            chromo = self.current[uid]
        except KeyError:
            chromo = None
        return chromo

    def get_chromo_from_previous(self, uid):
        '''
            Returns a chromosome from the previous generation which has uid
            equal to `uid'. If there isn't such chromosome, returns None.
        '''
        try:
            chromo = self.previous[uid]
        except KeyError:
            chromo = None
        return chromo

    def get_all_from_current(self):
        '''
            Returns a generator for all chromosomes inside the
            current generation.
        '''
        return list(self.current.get_all())

    def get_all_from_previous(self):
        '''
            Returns a generator for all chromosomes inside the
            previous generation.
        '''
        return list(self.previous.get_all())

    def get_couple_from_current(self, different=True):
        '''
            Returns a tuple with two random chromosomes
            from the current generation inside the population.

            If different is set to True, the tuple will not
            contain the same chromosome twice.
        '''
        done = None

        while not done:
            male = self.current.select()
            female = self.current.select()

            if different:
                while female == male and female != None:
                    female = self.current.select()

            if male == None or female == None:
                done = True
            else:
                yield male, female


    def get_couple_from_previous(self, different=True):
        '''
            Same as get_couple_from_current() but the
            chromosomes selected come from the previous
            generation.
        '''

        done = None

        while not done:
            male = self.previous.select()
            female = self.previous.select()

            if different:
                while female == male and female != None:
                    female = self.previous.select()

            if male == None or female == None:
                done = True
            else:
                yield male, female

    def new_epoch(self, newgen=None):
        '''
            Changes the epoch and sets the current generation as previous.
            If newgen is set, it is assigned as the current generation.
            Otherwise, it creates a new one.
            Returns the current generation.
        '''
        self.epoch += 1
        self.previous = self.current

        if newgen == None:
            self.current = Generation(self.epoch)
        else:
            self.current = newgen

        return self.current

    def does_exist(self, uid):
        exists = False
        if self.get_chromo_from_current(uid) != None \
            or self.get_chromo_from_previous(uid) != None:
            exists = True
        return exists

    def set_fitness(self, uid, fitness):
        '''
            Sets the fitness to a chromosome of the current generation.
        '''
        self.current.set_fitness(uid, fitness)

    def set_previous_fitness(self, uid, fitness):
        '''
            Set fitness to chromosome of the previous generation.
        '''
        self.previous.set_fitness(uid, fitness)

    def delete_chromosome(self, uid):
        '''
            Deletes a chromosome from the current generation.
        '''
        self.current.delete(uid)

    def add_chromosome(self, chromo):
        '''
            Adds a chromosome to the current generation. Notice that, if the
            uid already exists in the current generation, it does nothing.
        '''
        if chromo.uid not in self.current:
            self.current[chromo.uid] = chromo

    def add_trace(self, uid, trace):
        '''
            Adds a trace to the target chromosome.
        '''
        chromo = self.current[uid]
        chromo.trace = trace
        self.current[uid] = chromo
        self.current.trace.update(trace)

    def elitism(self):
        '''
            Elitism is a selection process of genetic algorithms.

            Common genetic algorithms construct the new population just by
            retaining the chromosomes with the best fitness of the current
            generation and discarding the rest.

            Elitism (or elitist selection) is a different approach of selection.
            It is retaining the best individuals from the whole population.
            That means, if the parents (previous generation) have better fitness
            that the children (current generation), the children will be
            discarded but the parents will be retained. This indicates that the
            current generation was not valuable to the genetic algorithm.
        '''
        # for each chromosome in the current generation
        for chromo in self.current.get_all():

            # for each image in the monitored
            for image_name in chromo.trace.set_per_image.iterkeys():

                # for each basic block explored in the run
                for bbl in chromo.trace.set_per_image[image_name]:

                    # if there isn't any leader for this bbl
                    # set the current chromo
                    if self.image_leaders[image_name][bbl] == None:
                        self.image_leaders[image_name][bbl] = chromo
                    else:
                        # pick the fittest chromosome for this specific bbl
                        leader = self.image_leaders[image_name][bbl]

                        # if the fitness of the currect chromosome is better
                        # than the fitness of the leader, replace it
                        if leader.get_fitness() < chromo.get_fitness():
                            self.image_leaders[image_name][bbl] = chromo

                        ###     since we do not keep the number of times each
                        ###     bbl was hit, we compare the total number of
                        ###     basic blocks between the leader and the
                        ###     challenger chromosome. Enabling full trace
                        ###     logging did not seem worth for this feature,
                        ###     due to the memory issues we already have.

                        elif leader.get_fitness() == chromo.get_fitness():
                            if leader.trace.get_total() \
                                    < chromo.trace.get_total():
                                self.image_leaders[image_name][bbl] = chromo

        # find the unique chromosome that compose bbl leaders
        elite_chromosomes = {}

        # build the elite generation
        for bbl_leaders in self.image_leaders.itervalues():
            for chromo in bbl_leaders.itervalues():
                if chromo != None:
                    elite_chromosomes[chromo.uid] = chromo

        # create new generation
        new = self.new_epoch()
        new.extend(elite_chromosomes)

        # set up the generation metrics/stats
        for chromo in new.get_all():
            new.trace.update(chromo.trace)
            new.set_metrics(chromo.uid, chromo.metrics)
