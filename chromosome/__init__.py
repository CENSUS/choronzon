# Each parser class MUST implement the following methods:
#	parse: which will parse the given file
#	get_genes: a generator that yields all genes of the file
#	get_filter_manager: a filter_manager for the chromosome
# Also an important thing about the parsers is that should
# initialize the filter for each gene.
#
# Each gene class must implement the following methods:

from factory import *
from chromosome import *
