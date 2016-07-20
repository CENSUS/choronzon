class AbstractGene(object):
    data = None
    children = None

    def __init__(self):
        self.data = ''
        self.children = []

    def get_data(self):
        '''
            Returns the fuzzable data of the gene.
        '''
        return self.data

    def set_data(self, data):
        '''
            sets the data of this gene
        '''
        self.data = data

    def add_children(self, new):
        self.children.extend(new)

    def add_child(self, child, index=None):
        '''
            Adds a new gene children to the current gene.
        '''
        if index == None:
            self.children.append(child)
        else:
            self.children.insert(index, child)

    def get_children(self):
        '''
            Returns all the genes children. If the current gene
            has no children, then it returns an empty list.
        '''
        return self.children

    def remove_child(self, target):
        self.children.remove(target)

    def replace_child(self, target, new):
        '''
            It replaces a child with a new one. This function is not recursive
            which means it does not search for the ancestors of the gene's
            children. It returns the gene which will be replaced.
        '''
        index = self.children.index(target)
        old = self.children[index]
        self.children[index] = target
        return old

    def children_number(self):
        return len(self.children)

    def anomaly(self):
        '''
            Decides wheather this gene is fuzzable or not.
            True means that this gene should not be fuzzed.
        '''
        return False

    def mutate(self, mutator):
        '''
            uses a Mutator object to corrupt some of its data.
        '''
        data = mutator.mutate(self.get_data())
        self.set_data(data)

    def serialize(self):
        '''
            serializes its data and children's data into
            a bytestring.
        '''
        data = self.get_data()
        if data == None:
            data = ''
        for child in self.children:
            data += child.serialize()
        return data

    def is_equal(self, other):
        '''
            dummy
        '''
        return False

    def __str__(self):
        '''
            Convert the gene to bytestring.
        '''
        return self.to_str()

