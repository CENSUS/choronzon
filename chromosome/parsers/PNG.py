import os
import zlib
import math
import struct
import copy

import chromosome.gene as gene
import chromosome.serializer as serializer
import chromosome.deserializer as deserializer

PNG_SIGNATURE = '\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'


class PNGGene(gene.AbstractGene):
    '''
        The PNGGene represent a png chunk.

        Using the PNGDeserializer, we read the contents of a PNG file,
        and hold them into memory. Each PNG chunk corresponds to a PNGGene
        object. The contents of the PNG chunk are fuzzed in memory. We have
        the capability to fuzz specific parts of the chunk's contents. For
        example, it is useless to fuzz the CRC field of a PNG chunk.
    '''
    def __init__(self, chunk):
        super(PNGGene, self).__init__()
        self.length = chunk['length']
        self.name = chunk['name']
        self.data = chunk['data']
        self.crc = chunk['crc']

    def anomaly(self):
        '''
            If anomaly returns True, then the current
            gene should not be fuzzed.
        '''
        if self.length == 0:
            return True
        else:
            return False

    def is_equal(self, other):
        '''
            To identify PNG chunks of same type.
        '''
        if not isinstance(other, self.__class__):
            return False

        if self.name == other.name and PNGGene.asciiname(self.name) != 'IEND':
            return True
        else:
            return False

    # This function must be implemented in order 
    def serialize(self):
        '''
            This function is called to serialize in-memory data of a PNG chunk.
        '''
        self.fix_crc()

        bytestring = ''
        chunk_data = super(PNGGene, self).serialize()

        bytestring += struct.pack('>I', len(chunk_data))
        bytestring += struct.pack('>I', self.name)
        bytestring += chunk_data
        bytestring += struct.pack('>I', self.crc)

        return bytestring

    def fix_crc(self):
        '''
            re-calculates the Gene's CRC checksum.
        '''
        checksum = zlib.crc32(
            struct.pack('>I', self.name)
            )
        self.crc = zlib.crc32(
            self.data, checksum
            ) & 0xffffffff

    @staticmethod
    def asciiname(chunkname):
        '''
            Converts a chunk name to ascii and returns it.
        '''
        return '%c%c%c%c' % (
                (chunkname >> 24) & 0xFF,
                (chunkname >> 16) & 0xFF,
                (chunkname >> 8) & 0xFF,
                (chunkname & 0xFF)
                )


class PNGSerializer(serializer.BaseSerializer):
    '''
        The PNG Serializer.

        This class is used to serialize a tree of PNGGenes into a file. Since
        PNG is just a chunk-based format, there is no a tree of genes, but
        a list of genes. During the serialization, the CRC of each chunk is
        fixed and some chunks, which are required to be compressed, are
        deflated using the zlib.
    '''
    def __init__(self):
        super(PNGSerializer, self).__init__()

    @staticmethod
    def deflate_idat_chunks(genes):
        '''
            deflate_idat_chunks takes as input a number of genes. Data stored
            only in IDAT genes is collected in a bytestring and it is compressed
            using the zlib module. Then the compressed bytestring is divided
            again and copied in genes. This functions returns a list with the
            deflated genes. Keep in mind that this function is working with a
            deep copy of the genes given as input. Hence, do not worry for your
            data in the genes passed as argument.
        '''
        indices = list()
        deflated_genes = copy.deepcopy(genes)
        datastream = str()

        for idx, curr_gene in enumerate(genes):
            if PNGGene.asciiname(curr_gene.name) == 'IDAT':
                indices.append(idx)
                datastream += curr_gene.get_data()

        comp = zlib.compress(datastream)
        idatno = len(indices)

        if idatno > 0:
            chunk_len = int(math.ceil(float(len(comp)) / float(idatno)))

            for cnt, index in enumerate(indices):
                start = cnt * chunk_len
                if index != indices[-1]:
                    deflated_genes[index].set_data(
                            comp[start : start+chunk_len])
                else:
                    deflated_genes[index].set_data(
                            comp[start : ]
                            )
                deflated_genes[index].length = len(
                        deflated_genes[index].get_data()
                        )

        return deflated_genes

    def serialize(self, genes):
        '''
            This method serializes each one of the genes given as argument. The
            serialized bytestring of each of the genes is appended in a buffer
            that contains the PNG header. The bytestring of the whole PNG
            is returned.
        '''
        bytestring = PNG_SIGNATURE
        deflated_genes = PNGSerializer.deflate_idat_chunks(genes)
        bytestring += super(PNGSerializer, self).serialize(deflated_genes)
        return bytestring


class PNGDeserializer(deserializer.BaseDeserializer):
    '''
        A parser for PNG files.

        This class is used to parse the chunks of a PNG file and construct
        PNGGene objects with the contents of the chunks. Moreover, the
        deserializer will perform decompression to the zipped data in order to
        fuzz them directly in memory.
    '''
    fsize = None
    fstream = None
    chunks = None

    def __init__(self):
        super(PNGDeserializer, self).__init__()
        self.fsize = 0
        self.fstream = None
        self.chunks = list()

    def deserialize(self, filename):
        '''
            Parses the chosen PNG file.
        '''
        # initialize input file
        genes = list()

        # open and read PNG header
        self._prepare(filename)
        self._parse_signature()

        # parse data chunks
        for chunk in self._parse_chunks():
            self.chunks.append(chunk)

        # decompress IDAT chunks (zlib streams)
        self._inflate_idat_chunks()

        # initialize gene list with deflated chunks
        for chunk in self.chunks:
            genes.append(PNGGene(chunk))

        self.fstream.close()
        self.fsize = 0
        self.chunks = list()

        return genes

    def _inflate_idat_chunks(self):
        '''
            This method takes all IDAT PNG chunks that was read and decompress
            their data using zlib module.
        '''
        datastream = str()
        indices = list()

        for idx, chunk in enumerate(self.chunks):
            if PNGGene.asciiname(chunk['name']) == 'IDAT':
                datastream += chunk['data']
                indices.append(idx)

        decomp = zlib.decompress(datastream)

        idatno = len(indices)
        chunk_len = int(math.ceil(float(len(decomp)) / float(idatno)))

        for cnt, index in enumerate(indices):
            start = cnt * chunk_len

            if index != indices[-1]:
                self.chunks[index]['data'] = decomp[start : start + chunk_len]
            else:
                self.chunks[index]['data'] = decomp[start:]

            self.chunks[index]['length'] = len(self.chunks[index]['data'])


    def _parse_signature(self):
        '''
            The first 8 bytes of every PNG image must be the signature.
        '''
        signature = self.fstream.read(8)
        assert len(signature) == 8

    def _parse_chunks(self):
        '''
            A generator that parses all chunks of the chosen PNG image.
        '''
        index = 0
        while self.fsize > self.fstream.tell():
            index += 1
            chunk = dict()
            chunk['index'] = index
            chunk['length'], = struct.unpack('>I', self.fstream.read(4))
            chunk['name'], = struct.unpack('>I', self.fstream.read(4))
            chunk['data'] = self.fstream.read(chunk['length'])
            chunk['crc'], = struct.unpack('>I', self.fstream.read(4))

            yield chunk

    def _get_filesize(self):
        '''
            Returns the file size.
        '''
        where = self.fstream.tell()
        self.fstream.seek(0, 2)
        size = self.fstream.tell()
        self.fstream.seek(where, 0)
        return size

    def _prepare(self, filename):
        '''
            Preparation before parsing.
        '''
        if not os.path.isfile(filename):
            raise IOError('%s is not a regural file.' % filename)

        self.chunks = list()
        self.fstream = open(filename, 'rb')
        self.fsize = self._get_filesize()

