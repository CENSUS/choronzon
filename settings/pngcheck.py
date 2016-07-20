CampaignName = 'pngcheck-campaign'
Parser = 'PNG'
InitialPopulation = '/tmp/png/'

FitnessAlgorithms = {
    'BasicBlockCoverage': 0.6,
    'CodeCommonality': 0.4
        }

Recombinators = (
    'Recombinator',
    'NullRecombinator',
    'ChildrenSelector',
    'SimilarGeneSelector',
    'ParentChildrenSwap',
    'ShuffleSiblings',
    'RandomGeneSwapRecombinator',
    'RemoveGeneRecombinator',
    'DuplicateGeneRecombinator',
    'AdditiveSimilarGeneCrossOver',
    'SimilarGeneSwapRecombinator',
    'RandomGeneInsertRecombinator',
    'SimilarGeneInsertRecombinator'
)

Mutators = (
    'QuotedTextualNumberMutator',
    'RemoveLines',
    'RepeatLine',
    'SwapLines',
    'SwapAdjacentLines',
    'PurgeMutator',
    'SwapByte',
    'SwapWord',
    'ByteNullifier',
    'IncreaseByOneMutator',
    'DecreaseByOneMutator',
    'ProgressiveIncreaseMutator',
    'ProgressiveDecreaseMutator',
    'SwapDword',
    'SetHighBitFromByte',
    'DuplicateByte',
    'RemoveByte',
    'RandomByteMutator',
    'AddRandomData',
    'NullMutator'
)

Disassembler = 'IDADisassembler'
DisassemblerPath = '/home/user/ida-6.9'

KeepGenerations = True

# Pintool related settings
Timeout = 10

Command = '/usr/bin/pngcheck %s'
Whitelist = ('/usr/bin/pngcheck',)
