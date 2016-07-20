'''
    evaluator.py contains code that divides the chromosomes
    of a generation to elite and non-interesting. Also, it's responsible
    for metric normalization and fitness calculation.
'''

import sortedcontainers as sc

import configuration
import campaign

class Metric(object):
    '''
        Base Metric class that is inherited by every
        user specified metric algorithm.
    '''
    trace = None
    value = None

    def __init__(self, chromo):
        '''
            normal initializer
        '''
        self.chromo = chromo
        self.value = 0.0

    def get_normal(self, **kwargs):
        '''
            returns the normalized metric value
        '''
        return self.value

    @classmethod
    def calculate(cls, chromo, **kwargs):
        '''
            automatic wrapper that returns the value
            of get_normal().
        '''
        obj = cls(chromo)
        return obj.get_normal(**kwargs)

class BasicBlockCoverage(Metric):
    '''
        Returns the percentage of the total basic block that
        was hit in all images.
    '''
    def get_normal(self, **kwargs):
        if 'cache' not in kwargs:
            raise KeyError('Cache not found')

        unique_trace = self.chromo.trace.get_unique_total()
        count = 0x0
        for img in kwargs['cache']:
            count += kwargs['cache'][img].get_count()

        if count == 0x0:
            return 0.0

        return unique_trace / float(count)

class UniversalPathUniqueness(Metric):
    '''
        Returns the percentage of the bbls of the trace of the given chromosome
        that was not hit by any other chromosome in the population.
    '''
    def get_normal(self, **kwargs):
        # assume that this chromosome is in the current generation
        other = kwargs['previous']
        this = kwargs['current']

        # check if the assumption is correct
        if kwargs['previous'] != None:
            if self.chromo in kwargs['previous']:
                this = kwargs['previous']
                other = kwargs['current']

        # holds the unique basic blocks per image (key)
        unique = {}

        # if other != None, means that this isn't the first generation
        if other != None:
            # unique will hold all the bbls that was hit in this chromo
            # and was not hit by the other generation
            for img, uniq in self.chromo.trace.get_difference_per_image(
                    other.trace
                    ):
                unique[img] = uniq
        else:
            # if this is the first generation, unique corresponds to
            # all the bbls of the trace
            for img in self.chromo.trace.images:
                unique[img] = sc.SortedSet().update(
                        self.chromo.trace.set_per_image[img]
                        )
        # iterate through all chromos in this generation (unless myself)
        for chromo in this:
            if chromo.uid == self.chromo.uid:
                continue
            for img in chromo.trace.images:
                # remove from the unique the bbls that was hit by other
                # chromosomes in my generation
                unique[img] -= chromo.trace.set_per_image[img]

        # faults will be equal to the basic blocks that exist only in myself
        faults = 0x0
        for img in unique:
            faults += len(unique[img])

        return faults / float(self.chromo.trace.get_unique_total())

class GenerationUniqueness(Metric):
    '''
        Returns the percentage of the bbls of the trace of the given chromosome
        that was not hit by any other chromosome in the other generation.
    '''
    def get_normal(self, **kwargs):
        # other is `previous' if the chromosome belongs to
        # current generation otherwise it's `current' if the
        # chromosome belongs to previous generation
        other = kwargs['previous']

        if kwargs['previous'] != None:
            if self.chromo in kwargs['previous']:
                other = kwargs['current']

        # if other == None, this is the first generation
        if other == None:
            return 1.0

        unique = {}

        for img, uniq in self.chromo.trace.get_difference_per_image(
                other.trace
                ):
            unique[img] = uniq

        faults = 0x0
        for img in unique:
            faults += len(unique[img])

        return faults / float(self.chromo.trace.get_unique_total())

class CodeCommonality(Metric):
    '''
        The percentage of the unique BBLs hit
    '''
    def get_normal(self, **kwargs):
        unique_trace = self.chromo.trace.get_unique_total()
        total_trace = self.chromo.trace.get_total()
        if total_trace == 0x0:
            return 0.0
        return total_trace / float(unique_trace)

class Evaluator(object):
    '''
        Evaluator class is the top-level management class
        that handles the calling the appropriate functions
        and incorporates the logic of the evaluation.
    '''
    cache = None
    configuration = None
    weights = None
    algorithms = None
    population = None

    def __init__(self, cache, configfile=None):
        self.cache = cache
        self.configuration = configuration.Configuration(configfile)
        self.campaign = campaign.Campaign()
        self.load_metric_algorithms(
                self.configuration['FitnessAlgorithms']
                )

    def load_metric_algorithms(self, algorithms=None):
        '''
            accepts a dictionary of the algorithm class names and
            their matching weights and loads them into a class
            instance by searching the module globals.
        '''
        if algorithms == None:
            algorithms = {}
        self.weights = algorithms
        self.algorithms = {}
        for name in algorithms:
            self.algorithms[name] = globals()[name]

    def calculate_metrics(self, chromo):
        '''
            use the implemented algorithms above to
            calculate the metrics for a given chromosome.
        '''
        previous = None
        if self.population.previous != None:
            previous = self.population.previous

        metrics = {}

        # This is because we want to log the metrics for each chromosome
        for name in self.algorithms:
            algo = self.algorithms[name]
            metric = algo.calculate(
                    chromo,
                    cache=self.cache,
                    previous=previous,
                    current=self.population.current
                    )
            metrics[name] = metric

        return metrics

    def calculate_previous_gen_metrics(self):
        '''
            calculates and sets the (non normalized) metrics
            for each individual chromosome.
        '''
        if self.population.previous == None:
            return

        for chromo in self.population.previous.get_all():
            metrics = self.calculate_metrics(chromo)
            self.population.previous.set_metrics(chromo.uid, metrics)

    def calculate_current_gen_metrics(self):
        '''
            calculates and sets the metrics for each
            individual chromosome.
        '''
        for chromo in self.population.current.get_all():
            metrics = self.calculate_metrics(chromo)
            self.population.current.set_metrics(chromo.uid, metrics)

    def get_population_max_metrics(self):
        '''
            returns the maximum value for each metric
        '''
        if self.population.previous == None:
            return self.population.current.max_metrics

        globmax = {}
        for name, prev in self.population.previous.max_metrics.iteritems():
            curr = self.population.current.max_metrics[name]
            globmax[name] = max(prev, curr)

        return globmax

    def get_population_min_metrics(self):
        '''
            returns the minimum value for each metric
        '''
        if self.population.previous == None:
            return self.population.current.min_metrics

        globmin = {}
        for name, prev in self.population.previous.min_metrics.iteritems():
            curr = self.population.current.min_metrics[name]
            globmin[name] = min(prev, curr)

        return globmin

    def get_normalized_metrics(self):
        '''
            normalizes the metrics retrieved for each chromosome
            in the population (previous AND current generation)
            using the classical:

                x_norm = (x - xmin) / (xmax - xmin)
        '''
        globmax = self.get_population_max_metrics()
        globmin = self.get_population_min_metrics()

        maxmin = {}
        for name in globmax:
            val = float(globmax[name] - globmin[name])
            if val == 0.0:
                maxmin[name] = 1
            else:
                maxmin[name] = val

        current = {}

        # this applies to both current and previous
        # current[chromo.uid][metric_name] = metric_value
        for chromo in self.population.current.get_all():
            current[chromo.uid] = {}
            for name in chromo.metrics:
                current[chromo.uid][name] = (
                        chromo.metrics[name] - globmin[name]
                        ) / maxmin[name]

        previous = {}
        if self.population.previous != None:
            for chromo in self.population.previous.get_all():
                previous[chromo.uid] = {}
                for name in chromo.metrics:
                    previous[chromo.uid][name] = (
                            chromo.metrics[name] - globmin[name]
                            ) / maxmin[name]

        return previous, current

    def calculate_fitness(self, metrics):
        '''
            uses the weights provided in the configuration
            to calculate the individual fitness of a
            chromosome.
        '''
        fitness = 0.0

        for name in metrics:
            weight = self.weights[name]
            fitness += weight * metrics[name]

        return fitness

    def set_population_fitness(self):
        '''
            uses the normalized metrics to compute
            the fitness for both the previous and
            the current generation. It then proceeds
            to set the fitness for every chromosome in
            the population.
        '''
        previous, current = self.get_normalized_metrics()

        self.campaign.log('From the previous generation')
        for chromo_uid in previous:
            fitness = self.calculate_fitness(previous[chromo_uid])
            self.campaign.log('Uid: %s, fitness: %f' % (chromo_uid, fitness))
            self.population.set_previous_fitness(
                    chromo_uid, fitness
                )

        self.campaign.log('From the current generation')
        for chromo_uid in current:
            fitness = self.calculate_fitness(current[chromo_uid])
            self.campaign.log('Uid: %s, fitness: %f' % (chromo_uid, fitness))
            self.population.set_fitness(
                    chromo_uid, fitness
                )

    def evaluate(self, population):
        '''
            computes the metrics for every chromosome
            in the current generation.

            Then it normalizes the metrics and calculates
            the fitness for every chromosome in the
            *population*.

            This means that the results are normalized
            for both previous and current generations.
        '''
        self.campaign.log('Evaluating the population.')
        self.population = population
        self.calculate_previous_gen_metrics()
        self.calculate_current_gen_metrics()
        self.set_population_fitness()

        if self.population.previous == None:
            self.population.current.clear_metrics()

        return True
