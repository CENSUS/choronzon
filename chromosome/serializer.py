class BaseSerializer(object):
    '''
    API for parsers.
    '''
    def __init__(self):
        pass

    def serialize(self, genes):
        data = ''
        for gene in genes:
            data += gene.serialize()
        return data
