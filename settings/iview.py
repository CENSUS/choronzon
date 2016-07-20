# Name of the campaign
CampaignName = 'iview-campaign'

# Name of the parser module. The parser module must be
# in the chromosome/parsers directory.
Parser = 'PNG'

# The path of the initial corpus
InitialPopulation = 'C:\\tmp\\png'

# The fitness algorithms that will be used by Chronzon
# and the weight of each one. Currently, two algorithms
# are implemented, the BasicBlockCoverage and CodeCommonality.
FitnessAlgorithms = {
    'BasicBlockCoverage': 0.5,
    'CodeCommonality': 0.3
        }

# A tuple with the Recombinators that will be used during the fuzzing.
# Users are encouraged to comment out the algorithms that they think
# they are not effective when fuzzing a specific target format. However,
# Choronzon has an internal evaluation system in order to use more often
# the effective algorithms.
Recombinators = (
    'AdditiveSimilarGeneCrossOver',
    'DuplicateGeneRecombinator',
    'RemoveGeneRecombinator',
    'RemoveGeneRecombinator',
    'ShuffleSiblings',
    'ParentChildrenSwap',
    'SimilarGeneSwapRecombinator',
    'RandomGeneSwapRecombinator',
    'RandomGeneInsertRecombinator',
    )

# A tuple with the Mutators that will be used during the fuzzing.
Mutators = (
    'RandomByteMutator',
    'AddRandomData',
    'RandomByteMutator',
    'RemoveByte',
    'SwapAdjacentLines',
    'SwapLines',
    'RepeatLine',
    'RemoveLines',
    'QuotedTextualNumberMutator',
    'PurgeMutator',
    'SwapWord',
    'SwapDword',
    )

# If KeepGenerations is True the seedfiles of each generation will be stored
# in the campaign directory. Keep in mind though, that this may lead to run out of
# free space, if the fuzzer runs of a long time.
KeepGenerations = True

# The name of the disassembler module that will be used.
# Currently, only IDA is supported.
Disassembler = 'IDADisassembler'
DisassemblerPath = 'C:\\Program Files (x86)\\IDA 6.9'

# The command that will be executed to test the target application.
# Note that %s will be replaced by the fuzzed file.
Command = '\"C:\\Program Files\\IrfanView\\i_view64.exe\" %s'

# A tuple with the modules that will be instrumented in order to collect
# stats to calculate the fitness. Full path of the modules is required.
# Please note, that Whitelist must be a tuple even there is only one module.
Whitelist = ('C:\\Program Files\\IrfanView\\i_view64.exe',)
