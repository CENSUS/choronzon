import random
import bisect
import fuzzers.recombinators as recombinators
import fuzzers.mutators as mutators
from configuration import Configuration
import world

class WeightedSelector(world.NaiveSelector):
    '''
        This class implements a selection algorithm. Each of the items can be
        assigned with a weight in order to control if it is more likely
        to select it or not.
    '''
    def __init__(self, objlist, initial=0):
        super(WeightedSelector, self).__init__(objlist)

    def select(self):
        '''
            selects a random object from the object list
            based according to weights set.
        '''
        if not self.objdict.keys():
            return None

        while True:
            objkey = random.choice(self.objdict.keys())
            if self.unfair_coinflip(self.objdict[objkey]):
                return objkey

    def set_weight(self, key, weight):
        self.objdict[key] = weight

    def get_weight(self, key):
        return self.objdict[key]

class Lottery(object):
    '''
        the Lottery class is responsible of randomly selecting a winner from a
        pool of players, by randomly choosing a ticket from a pool of tickets.
        The number of tickets in the pool of tickets is the total of the score
        of each individual player. This means that the player's score is
        actually the number of tickets this player has "bought".
    '''
    players = None
    tickets = None
    ticket_number = None

    def __init__(self):
        self.players = []
        self.tickets = []
        self.ticket_number = 0x0

    def join(self, player, score):
        self.players.append(player)
        self.tickets.append(
                self.ticket_number
                )
        self.ticket_number += score

    def choose_ticket(self):
        return random.randrange(
                0, self.ticket_number
                )

    def choose_winner(self):
        ticket = self.choose_ticket()
        index = bisect.bisect(
                self.tickets,
                ticket
                )
        return self.players[index-1]

    @classmethod
    def run(cls, players):
        '''
            players is an iterable of
        '''
        obj = cls()
        for player in players:
            obj.join(player, player['score'])
        return obj.choose_winner()

class FuzzingStrategy(object):
    configuration = None
    recombinators = None
    mutators = None
    candidates = None

    def __init__(self):
        self.configuration = Configuration()
        self.initialize_recombinators()
        self.initialize_mutators()
        self.generate_candidates()

    def initialize_recombinators(self):
        self.recombinators = dict()
        for recombinator in self.configuration['Recombinators']:
            self.recombinators[recombinator] = getattr(
                    recombinators,
                    recombinator
                    )()

    def initialize_mutators(self):
        self.mutators = dict()
        for mutator in self.configuration['Mutators']:
            self.mutators[mutator] = getattr(
                    mutators,
                    mutator
                    )()

    def generate_candidates(self):
        self.candidates = dict()
        for rname, recombinator in self.recombinators.iteritems():
            for mname, mutator in self.mutators.iteritems():
                cid = '%s_%s' % (rname, mname)
                candidate = dict()
                candidate['cid'] = cid
                candidate['recombinator'] = recombinator
                candidate['mutator'] = mutator
                candidate['score'] = 0x1
                self.candidates[cid] = candidate

    def good(self, cid, score=1):
        this = self.candidates[cid]['score']
        self.candidates[cid]['score'] = max(this, score)

    def bad(self, cid, score=1):
        if self.candidates[cid]['score'] > 1:
            self.candidates[cid]['score'] -= score

    def select_candidate(self):
        return Lottery.run(self.candidates.values())

    def recombine(self, male, female):
        candidate = self.select_candidate()

        # XXX: implement a system that will be able to pretty-print the scores
        # of the mutators/recombinators.

        mutator = candidate['mutator']
        recombinator = candidate['recombinator']

        son, daughter = recombinator.recombine(
                male,
                female,
                mutator
                )

        son.fuzzer = candidate['cid']
        daughter.fuzzer = candidate['cid']

        return son, daughter
