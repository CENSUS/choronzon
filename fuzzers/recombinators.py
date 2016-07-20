'''
    Recombination is a feature of Choronzon, which is not common amongst other
    fuzzers. Prerequisite of recombination is the knowledge of the basic
    structure of the file format. Thus, recombinators are built upon
    the gene/chrosome system of Choronzon. Recombinators use this knowledge,
    and try to alter the structure of the file instead of simply mutating their
    bits and bytes.
'''
import random
import copy
import fuzzers.mutators as mutators

class Recombinator(object):
    '''
        This is the recombinator's base class.
    '''
    def __init__(self):
        pass

    def choose_genes(self, chr1, chr2):
        '''
            Returns randomly one gene of each chromosome.
        '''
        all1 = chr1.get_all_genes()
        all2 = chr2.get_all_genes()

        if len(all1) < 1 or len(all2) < 1:
            return None, None

        return (
                random.choice(all1),
                random.choice(all2)
                )

    def mutate(self, gene, mutator=None):
        '''
            Fuzz a gene.
        '''
        if gene.anomaly():
            return gene

        # If the mutator is not specified, use the random byte mutator.
        # This behaviour may change in the future.
        if mutator == None:
            mutator = mutators.RandomByteMutator()

        gene.mutate(mutator)
        return gene

    def recombine(self, chr1, chr2, mutator=None):
        '''
            The recombination should be implemented in this function.
        '''
        return chr1, chr2

class NullRecombinator(Recombinator):
    '''
        Just fuzz one gene of each chromosome. Do not recombine.
    '''
    def __init__(self):
        super(NullRecombinator, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        gene1, gene2 = self.choose_genes(chr1, chr2)
        if gene1 == None or gene2 == None:
            return chr1, chr2

        self.mutate(gene1, mutator)
        self.mutate(gene2, mutator)

        return chr1, chr2

class ChildrenSelector(Recombinator):
    '''
        This class is a Selector, which means that implements only the
        choose_genes function.
    '''
    def __init__(self):
        super(ChildrenSelector, self).__init__()

    def choose_genes(self, chr1, chr2):
        '''
            Picks one non-root node from each chromosome/
        '''
        # get_all_genes returns all genes
        genes1 = chr1.get_all_genes()
        # get_genes returns only the root nodes
        parents1 = chr1.get_genes()
        child1 = None

        for random_gene in random.sample(genes1, len(genes1)):
            if random_gene not in parents1:
                child1 = random_gene
                break

        genes2 = chr2.get_all_genes()
        parents2 = chr2.get_genes()
        child2 = None

        for random_gene in random.sample(genes2, len(genes2)):
            if random_gene not in parents2:
                child2 = random_gene
                break

        return child1, child2


class SimilarGeneSelector(Recombinator):
    '''
        Selects similar genes from two chromosomes
    '''

    def __init__(self):
        super(SimilarGeneSelector, self).__init__()

    def choose_genes(self, chr1, chr2):
        genes = chr1.get_all_genes()
        for gene1 in random.sample(genes, len(genes)):
            for gene2 in chr2.get_all_genes():
                if gene2.is_equal(gene1):
                    return gene1, gene2
        return None, None


class ParentChildrenSwap(ChildrenSelector, Recombinator):
    '''
        Changes the hierarchy (children - parent) for one gene
        in each chromosome.
    '''
    def __init__(self):
        super(ParentChildrenSwap, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        child1, child2 = self.choose_genes(chr1, chr2)
        if child1 == None or child2 == None:
            return chr1, chr2

        parent1 = chr1.find_parent(child1)
        # index-th position of the parent's children list points to
        # the selected child. keep this for later
        index = parent1.children.index(child1)

        siblings = parent1.children
        # move the children's ancestors to the parent
        parent1.children = child1.children
        # and set the children of the parent (siblings of the child)
        # as ancestors of the child
        child1.children = siblings
        child1.children[index] = parent1

        parent2 = chr2.find_parent(child2)
        index = parent2.children.index(child2)

        siblings = parent2.children
        parent2.children = child2.children
        child2.children = siblings
        child2.children[index] = parent2

        return chr1, chr2

class ShuffleSiblings(ChildrenSelector, Recombinator):
    '''
        Chooses two non-root nodes of each chromosome and shuffle them and
        their siblings.
    '''
    def __init__(self):
        super(ShuffleSiblings, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        child1, child2 = self.choose_genes(chr1, chr2)
        if child1 == None or child2 == None:
            return chr1, chr2

        parent1 = chr1.find_parent(child1)
        parent2 = chr2.find_parent(child2)

        random.shuffle(parent1.children)
        random.shuffle(parent2.children)

        return chr1, chr2


class RandomGeneSwapRecombinator(Recombinator):
    '''
        Chooses a gene randomly from each chromosome and swaps them.
    '''
    def __init__(self):
        super(RandomGeneSwapRecombinator, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        old_gene1, old_gene2 = self.choose_genes(chr1, chr2)
        if old_gene1 == None or old_gene2 == None:
            return chr1, chr2

        # Probably deep copy is not required here
        gene1 = copy.deepcopy(old_gene1)
        gene2 = copy.deepcopy(old_gene2)

        gene1 = self.mutate(gene1, mutator)
        gene2 = self.mutate(gene2, mutator)

        chr2.replace_gene(old_gene2, gene1)
        chr1.replace_gene(old_gene1, gene2)

        return chr1, chr2

class RemoveGeneRecombinator(Recombinator):
    '''
        Remove randomly one gene from each chromosome.
    '''
    def __init__(self):
        super(RemoveGeneRecombinator, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        old_gene1, old_gene2 = self.choose_genes(chr1, chr2)
        if old_gene1 == None or old_gene2 == None:
            return chr1, chr2

        chr1.remove_gene(old_gene1)
        chr2.remove_gene(old_gene2)

        return chr1, chr2

class DuplicateGeneRecombinator(Recombinator):
    '''
        Duplicates and muates one gene from each chromosome.
    '''
    def __init__(self):
        super(DuplicateGeneRecombinator, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        old_gene1, old_gene2 = self.choose_genes(chr1, chr2)
        if old_gene1 == None or old_gene2 == None:
            return chr1, chr2

        gene1 = copy.deepcopy(old_gene1)
        gene2 = copy.deepcopy(old_gene2)

        self.mutate(gene1, mutator)
        self.mutate(gene2, mutator)

        parent1 = chr1.find_parent(old_gene1)
        if parent1 == None:
            index = chr1.genes.index(old_gene1)
            chr1.genes.insert(index, gene2)
        else:
            parent1.add_child(gene2)

        parent2 = chr2.find_parent(old_gene2)
        if parent2 == None:
            index = chr2.genes.index(old_gene2)
            chr2.genes.insert(index, gene2)
        else:
            parent2.add_child(gene2)

        return chr1, chr2

class AdditiveSimilarGeneCrossOver(SimilarGeneSelector, Recombinator):
    '''
        Finds one similar gene in each chromosome. Inserts the one
        to the other chromosome as sibling of the similar gene.
    '''
    def __init__(self):
        super(AdditiveSimilarGeneCrossOver, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        old_gene1, old_gene2 = self.choose_genes(chr1, chr2)
        if old_gene1 == None or old_gene2 == None:
            return chr1, chr2

        gene1 = copy.deepcopy(old_gene1)
        gene2 = copy.deepcopy(old_gene2)

        self.mutate(gene1, mutator)
        self.mutate(gene2, mutator)

        parent1 = chr1.find_parent(old_gene1)
        if parent1 == None:
            index = chr1.genes.index(old_gene1)
            chr1.genes.insert(index, gene2)
        else:
            parent1.add_child(gene2)

        parent2 = chr2.find_parent(old_gene2)
        if parent2 == None:
            index = chr2.genes.index(old_gene2)
            chr2.genes.insert(index, gene1)
        else:
            parent2.add_child(gene1)

        return chr1, chr2


class SimilarGeneSwapRecombinator(SimilarGeneSelector,
                                    RandomGeneSwapRecombinator):
    '''
        Chooses one gene randomly from one parent and then it searches if
        there's a identical one in the other parent. If this is true,
        it swaps them. Otherwise, it swaps two genes randomly.
    '''
    def __init__(self):
        super(SimilarGeneSwapRecombinator, self).__init__()

class RandomGeneInsertRecombinator(Recombinator):
    '''
        Chooses a Gene randomly from one chromosome and inserts it
        to the other (randomly again). It does the same to the
        other chromosome.
    '''
    def __init__(self):
        super(RandomGeneInsertRecombinator, self).__init__()

    def recombine(self, chr1, chr2, mutator=None):
        old_gene1, old_gene2 = self.choose_genes(chr1, chr2)

        gene1 = copy.deepcopy(old_gene1)
        gene2 = copy.deepcopy(old_gene2)

        gene1 = self.mutate(gene1, mutator)
        gene2 = self.mutate(gene2, mutator)

        parent1 = chr1.find_parent(old_gene1)
        if parent1 == None:
            # could not find the parent of g1 that means it is a root node
            # just insert the new gene after the chosen one.
            index = chr1.genes.index(old_gene1)
            chr1.genes.insert(index, gene2)
        else:
            # make the fuzzed gene of the chromo2
            parent1.add_child(gene2)

        parent2 = chr2.find_parent(old_gene2)
        if parent2 == None:
            index = chr2.genes.index(old_gene2)
            chr2.genes.insert(index, gene1)
        else:
            parent2.add_child(gene1)

        return chr1, chr2

class SimilarGeneInsertRecombinator(SimilarGeneSelector,
                                        RandomGeneInsertRecombinator):
    '''
        Selects similar genes from the two chromosomes and
        inserts each one to the other chromosome.
    '''

    def __init__(self):
        super(SimilarGeneInsertRecombinator, self).__init__()
