'''
    The Chromosome module.
'''
import os
import copy
import random
import cPickle

class Chromosome(object):
    '''
        The Chromosome class represents a deserialized file.

        Each chromosome class contains various information about the file.
        For example, the fitness and the metrics, which indicate how "favorable"
        is the file for the fuzzing process.

        The basic structures of the file format are defined by genes. Genes form
        a tree-like structure, in which the children nodes are usually
        sub-structures of their parents. To get a better understanding of this,
        in the XML format you may think as a top-level gene the outter tag
        and as a child gene the inner tag.

        Notice that each chromosome contains only the top level genes of a file.
        The relationship between the genes is not stored in Chromosome class.

        Additionally, a Chromosome is able to parse this tree of genes and
        serialize them in a file using the serilizer given as argument to
        Chromosome's constructor.
    '''
    trace = None
    genes = None
    serializer = None
    deserializer = None
    metrics = None
    fitness = None
    fuzzer = None
    uid = None
    processed = None

    def __init__(self, serializer=None, deserializer=None):
        self.genes = list()
        self.serializer = serializer()
        self.deserializer = deserializer()
        self.metrics = {}
        self.fitness = 0.0
        self.uid = self.new_uid()
        self.processed = False

    def __len__(self):
        return len(self.genes)

    def __str__(self):
        return self.serialize()

    def new_uid(self):
        '''
            Assign a new random UID to the chromosome.
        '''
        self.uid = random.randint(0, 0xFFFFFFFFFFFFFFFF)
        return self.uid

    def clone(self):
        '''
            Clone the chromosome object, but assign a new unique identifier
            to the new chromosome.
        '''
        newchr = copy.deepcopy(self)
        newchr.new_uid()
        return newchr

    def set_metrics(self, met):
        '''
            Set the metrics to the chromosome.
        '''
        self.metrics = met

    def get_metrics(self):
        '''
            Get the metrics from the chromosome.
        '''
        return self.metrics

    def set_fitness(self, fit):
        '''
            Sets the fitness to the current chromosome.
        '''
        self.fitness = fit

    def get_fitness(self):
        '''
            Gets the fitness from the current chromosome.
        '''
        return self.fitness

    def get_genes(self):
        '''
            Returns only the root nodes of the genes in the current chromsome.
        '''
        return self.genes

    def get_all_genes(self):
        '''
            Returns all genes of the current chromosome.
        '''
        return self._get_all_ancestors(self.get_genes())

    def _get_all_ancestors(self, genes):
        '''
            Returns a list with all ancestor genes (including the input genes)
        '''
        ancestors = []

        for parent_gene in genes:
            # add itself in the list
            ancestors.append(parent_gene)
            # for every children of the current gene
            for child in parent_gene.get_children():
                # if the child of the current gene contains children,
                # call _get_all_ancestors recursively
                if child.children_number() > 0:
                    ancestors.extend(
                                        self._get_all_ancestors(
                                              child.get_children()
                                        )
                                    )
                else:
                    ancestors.append(child)

        return ancestors

    def _internal_find_parent(self, root, target):
        '''
            A breadth first greedy search algorithm. Given a root node
            it returns the parent gene of the target. Returns None if the
            parent could not be found.
        '''
        parent = None

        if target in root.get_children():
            return root

        for child in root.get_children():
            parent = self._internal_find_parent(child, target)
            if parent != None:
                break

        return parent

    def find_parent(self, child):
        '''
            Finds and returns the parent of the gene given. If the gene is
            a root level gene, it returns None. On the other hand, if
            the gene does not belong to this chromosome, it raises
            a ValueError exception.
        '''
        if child in self.genes:
            return None

        parent = None

        for gene in self.genes:
            parent = self._internal_find_parent(gene, child)
            if parent != None:
                break

        if parent != None:
            return parent
        else:
            raise ValueError('Unable to find parent of gene.')

    def replace_gene(self, target, new):
        '''
            Replaces the target gene with new. Returns the replaced gene.
        '''
        old = None

        if target in self.genes:
            index = self.genes.index(target)
            old = self.genes[index]
            self.genes[index] = new
        else:
            parent = self.find_parent(target)
            old = parent.replace_child(target, new)
        return old

    def remove_gene(self, target):
        '''
            Removes a Gene from the chromosome. If the Gene does not exist,
            it raises a ValueError exception.
        '''
        parent = self.find_parent(target)
        if parent != None:
            parent.remove_child(target)
        else:
            self.genes.remove(target)

    def add_gene(self, gene):
        '''
            Appends a top level gene in the chromosome.
        '''
        self.genes.append(gene)

    def deserialize(self, filepath):
        '''
            Reads in a file and generates a list of genes. It uses a
            user-defined deserializer.
        '''
        self.genes = self.deserializer.deserialize(filepath)

    def serialize(self):
        '''
            Returns a bytestring that is the used as input to the target
            application. It uses a user-defined serializer.
        '''
        return self.serializer.serialize(self.genes)

    def dumps_chromosome(self, protocol=-1):
        '''
            It returns pickled bytestring containing the important attributes
            of the chromosome that are needed in order to write the chromosome
            in a file and restore it later or restore it from another Choronzon
            instance.
        '''
        important = [self.genes, self.metrics, self.uid, self.trace]
        return cPickle.dumps(important, protocol)

    def dump_chromosome(self, path, protocol=-1):
        '''
            Dumps the pickled bytestring into a file, indicated by path.
        '''
        if not os.path.exists(path):
            raise IOError('Could not find path: %s' % path)

        with open(path, 'wb') as fout:
            fout.write(self.dumps_chromosome(protocol))

    def loads_chromosome(self, data):
        '''
            Restores a chromosome from a pickled string.
        '''
        self.genes, self.metrics, self.uid, self.trace = cPickle.loads(data)

    def load_chromosome(self, path):
        '''
            Restores a chromosome from a pickled file.
        '''
        if not os.path.exists(path):
            raise IOError('Could not find path: %s' % path)

        with open(path, 'rb') as fin:
            self.genes, self.metrics, self.uid, self.trace = cPickle.load(fin)
