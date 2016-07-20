'''
    Mutator module contains a wide range of mutators. You can implement yours
    mutator in this module as well. All mutators must inherit the Mutator class
    and implement the mutate method. Choronzon, will eventually call every
    mutator, passing as parameters, a bytestring that needs to be fuzzed
    and a small integer. Every mutator must return the fuzzed data to the
    caller.
'''
import random
import re

class Mutator(object):
    '''
        This is the Mutator base class.
    '''
    def __init__(self):
        pass

    def mutate(self, data, howmany=0):
        '''
            data is the bytestring that will be mutated. howmany is usually a
            small integer given randomly by Choronzon. The fuzzed bytestring
            must return to the caller of this function.
        '''
        return data


class QuotedTextualNumberMutator(Mutator):
    '''
        Scans the bytestring in order to find number that are inside quotes.
        If there is such a number in the bytestring, it replaces it with a
        value from 0 to 0xFFFFFFFF.
    '''
    def __init__(self):
        super(QuotedTextualNumberMutator, self).__init__()

    def _coinflip(self, probability):
        ''' returns true with probability 1/probability'''
        return random.randint(0, probability) == 0

    def mutate(self, data, attribs=1):
        pattern = re.compile('\"\d+\"')
        fuzzed = ''
        to_be_fuzzed = []
        matched = []

        for match in pattern.finditer(data):
            matched.append(match.span())

        if len(matched) == 0 or attribs == 0:
            return data

        if len(matched) < attribs:
            attribs = len(matched)

        # first choose randomly which of the matched patterns will be found
        for _ in xrange(attribs):
            target = random.choice(matched)
            to_be_fuzzed.append(target)
            matched.remove(target)

        # we start to change the matched patterns backwards
        # otherwise, the indices of to_be_fuzzed variable would need to
        # recalcuated in every iteration
        to_be_fuzzed.reverse()
        for start, end in to_be_fuzzed:
            fuzzed = '%s\"%d\"%s' % (data[:start],
                                    random.randint(0, 0xFFFFFFFF),
                                     data[end:])
            data = fuzzed
        return data


class RemoveLines(Mutator):
    '''
        Removes a number of lines.
    '''
    def __init__(self):
        super(RemoveLines, self).__init__()

    def mutate(self, data, to_be_removed=1):
        lines = data.split('\n')

        if len(lines) < to_be_removed:
            return ''

        for _ in xrange(to_be_removed):
            line = random.choice(lines)
            lines.remove(line)

        return '\n'.join(lines)


class RepeatLine(Mutator):
    '''
        Duplicates a line.
    '''
    def __init__(self):
        super(RepeatLine, self).__init__()

    def mutate(self, data, repeat=1):
        lines = data.split('\n')

        if len(lines) < 1:
            return data

        index = random.randint(0, len(lines) - 1)
        target_line = lines[index]

        for _ in xrange(repeat):
            lines.insert(index, target_line)

        return '\n'.join(lines)


class SwapLines(Mutator):
    '''
        Grabs two lines and swaps them.
    '''
    def __init__(self):
        super(SwapLines, self).__init__()

    def mutate(self, data, _=1):
        lines = data.split('\n')
        if len(lines) < 2:
            return data

        index1 = random.randint(0, len(lines) - 2)
        index2 = random.randint(0, len(lines) - 2)

        tmp = lines[index1]
        lines[index1] = lines[index2]
        lines[index2] = tmp

        return '\n'.join(lines)


class SwapAdjacentLines(Mutator):
    '''
        Swap two adjacent lines.
    '''
    def __init__(self):
        super(SwapAdjacentLines, self).__init__()

    def mutate(self, data, howmany=1):
        lines = data.split('\n')
        if len(lines) < 3:
            return data

        for _ in xrange(howmany):
            index = random.randint(0, len(lines) - 2)
            tmp = lines[index]
            lines[index] = lines[index + 1]
            lines[index + 1] = tmp

        return '\n'.join(lines)


class PurgeMutator(Mutator):
    '''
        Deletes everything.
    '''
    def __init__(self):
        super(PurgeMutator, self).__init__()

    def mutate(self, data, _=0):
        return ''


class SwapByte(Mutator):
    '''
        Grabs two byte randomly and swaps them.
    '''
    def __init__(self):
        super(SwapByte, self).__init__()

    def mutate(self, data, _=2):
        fuzzed = ''

        if len(data) < 2:
            return data

        rnd1 = random.randint(0, len(data) - 1)
        if rnd1 >= 1:
            rnd2 = random.randint(0, rnd1 - 1)
        elif rnd1 + 1 <= len(data) - 1:
            rnd2 = random.randint(rnd1 + 1, len(data) - 1)

        min_rnd = min(rnd1, rnd2)
        max_rnd = max(rnd1, rnd2)

        byte1 = data[min_rnd]
        byte2 = data[max_rnd]

        fuzzed = data[:min_rnd]
        fuzzed += byte2
        fuzzed += data[min_rnd + 1:max_rnd]
        fuzzed += byte1
        fuzzed += data[max_rnd + 1:]

        return fuzzed


class SwapWord(Mutator):
    '''
        Grabs two word the swaps them.
    '''
    def __init__(self):
        super(SwapWord, self).__init__()

    def mutate(self, data, _=4):
        fuzzed = ''
        if len(data) < 4:
            return data

        rnd1 = random.randint(0, len(data) - 2)

        if rnd1 >= 2:
            rnd2 = random.randint(0, rnd1 - 2)
        elif rnd1 + 2 <= len(data) - 2:
            rnd2 = random.randint(rnd1 + 2, len(data) - 2)
        else:
            return data

        min_rnd = min(rnd1, rnd2)
        max_rnd = max(rnd1, rnd2)

        word1 = data[min_rnd:min_rnd + 2]

        word2 = data[max_rnd:max_rnd + 2]

        fuzzed = data[:min_rnd]
        fuzzed += word1
        fuzzed += data[min_rnd + 2:max_rnd]
        fuzzed += word2
        fuzzed += data[max_rnd + 2:]

        return fuzzed


class ByteNullifier(Mutator):
    '''
        Replace one (or more) bytes from the bytestring with \x00.
    '''
    def __init__(self):
        super(ByteNullifier, self).__init__()

    def mutate(self, data, _=1):
        fuzzed = ''
        if len(data) == 0:
            return data
        index = random.randint(0, len(data) - 1)

        fuzzed = '%s\x00%s' % (data[:index], data[index + 1:])
        return fuzzed


class IncreaseByOneMutator(Mutator):
    '''
        Increases the value of one (or more) byte(s) by one.
    '''
    def __init__(self):
        super(IncreaseByOneMutator, self).__init__()

    def mutate(self, data, howmany=1):
        if len(data) == 0:
            return data

        if len(data) < howmany:
            howmany = random.randint(1, len(data))

        fuzzed = data

        for _ in xrange(howmany):
            index = random.randint(0, len(data) - 1)
            if ord(data[index]) != 0xFF:
                fuzzed = '%s%c%s' % (
                        data[:index],
                        ord(data[index]) + 1,
                        data[index + 1:]
                    )
            else:
                fuzzed = '%s\x00%s' % (
                        data[:index],
                        data[index + 1:]
                        )
                        
            data = fuzzed

        return fuzzed


class DecreaseByOneMutator(Mutator):
    '''
        Decreases the value of one (or more) byte(s) by one.
    '''
    def __init__(self):
        super(DecreaseByOneMutator, self).__init__()

    def mutate(self, data, howmany=1):
        if len(data) == 0:
            return data

        if len(data) < howmany:
            howmany = random.randint(0, len(data) - 1)

        fuzzed = data
        for _ in xrange(howmany):
            index = random.randint(0, len(data) - 1)
            if ord(data[index]) != 0:
                fuzzed = '%s%c%s' % (
                        data[:index],
                        ord(data[index]) - 1,
                        data[index + 1:]
                    )
            else:
                fuzzed = '%s\xFF%s' % (
                    data[:index],
                    data[index + 1:]
                )
            data = fuzzed
        return fuzzed


class ProgressiveIncreaseMutator(Mutator):
    '''
        Increases the value of many consecutive bytes progressively.
        Specifically, the first byte will be increased by one, the second by
        two, the third by three and so on.
    '''
    def __init__(self):
        super(ProgressiveIncreaseMutator, self).__init__()

    def mutate(self, data, howmany=8):
        if len(data) < howmany:
            return data

        index = random.randint(0, len(data) - howmany)
        buf = ''
        fuzzed = ''

        for addend, curr in enumerate(xrange(index, index + howmany)):
            if addend + ord(data[curr]) > 0xFF:
                addend -= 0xFF
            buf += chr(ord(data[curr]) + addend)

        fuzzed = '%s%s%s' % (data[index:], buf, data[index + howmany:])
        return fuzzed


class ProgressiveDecreaseMutator(Mutator):
    '''
        Decreases the value of many consecutive bytes progressively.
        Specifically, the first byte will be decreased by one, the second by
        two, the third by three and so on.
    '''
    def __init__(self):
        super(ProgressiveDecreaseMutator, self).__init__()

    def mutate(self, data, howmany=8):
        if len(data) < howmany:
            return data
        index = random.randint(0, len(data) - howmany)
        buf = ''
        fuzzed = ''

        for subtrahend, curr in enumerate(xrange(index, index + howmany)):
            if ord(data[curr]) >= subtrahend:
                buf += chr(ord(data[curr]) - subtrahend)
            else:
                buf += chr(subtrahend - ord(data[curr]))

        fuzzed = '%s%s%s' % (data[index:], buf, data[index + howmany:])
        return fuzzed


class SwapDword(Mutator):
    '''
        Grabs two dwords from the bytestring and swaps them.
    '''
    def __init__(self):
        super(SwapDword, self).__init__()

    def mutate(self, data, _=8):
        fuzzed = ''

        if len(data) < 8:
            return data

        rnd1 = random.randint(0, len(data) - 4)

        if rnd1 >= 4:
            rnd2 = random.randint(0, rnd1 - 4)
        elif rnd1 + 4 <= len(data) - 4:
            rnd2 = random.randint(rnd1 + 4, len(data) - 4)
        else:
            return data

        min_rnd = min(rnd1, rnd2)
        max_rnd = max(rnd1, rnd2)

        dword1 = data[min_rnd:min_rnd + 4]
        dword2 = data[max_rnd:max_rnd + 4]


        fuzzed = data[:min_rnd]
        fuzzed += dword1
        fuzzed += data[min_rnd + 4:max_rnd]
        fuzzed += dword2
        fuzzed += data[max_rnd + 4:]

        return fuzzed


class SetHighBitFromByte(Mutator):
    '''
        Set the high bit from a byte.
    '''
    def __init__(self):
        super(SetHighBitFromByte, self).__init__()

    def mutate(self, data, _=1):
        fuzzed = ''

        if len(data) > 0:
            index = random.randint(0, len(data) - 1)
            byte = ord(data[index])
            byte |= 0x80
            fuzzed = data[:index]
            fuzzed += chr(byte)
            fuzzed += data[index + 1:]

        return fuzzed


class DuplicateByte(Mutator):
    '''
        Duplicate randomly a byte (or more) in the bytestring.
    '''
    def __init__(self):
        super(DuplicateByte, self).__init__()

    def mutate(self, data, howmany=1):
        fuzzed = ''

        if len(data) > howmany:
            howmany = len(data)

        for _ in xrange(howmany):
            index = random.randint(0, len(data) - 1)
            byte = data[index]
            fuzzed = data[:index]
            fuzzed += byte
            fuzzed += data[index:]

        return fuzzed


class RemoveByte(Mutator):
    '''
        Remove randomly a byte (or more) from the bytestring.
    '''
    def __init__(self):
        super(RemoveByte, self).__init__()

    def mutate(self, data, _=1):
        fuzzed = data
        if len(data):
            index = random.randint(0, len(data))
            fuzzed = data[:index]
            fuzzed += data[index + 1:]
        return fuzzed


class RandomByteMutator(Mutator):
    '''
        The old-time classic random byte mutator.
    '''
    def __init__(self):
        super(RandomByteMutator, self).__init__()

    def mutate(self, data, howmany=5):
        if len(data) < 2:
            return data
        for _ in xrange(howmany):
            tmp = random.randint(0, len(data) - 1)
            data = '%s%c%s' % (
                    data[:tmp],
                    random.randint(0, 0xFF),
                    data[tmp+1:]
                )
        return data


class AddRandomData(Mutator):
    '''
        Adds some random byte into the bytestring.
    '''
    def __init__(self):
        super(AddRandomData, self).__init__()

    def mutate(self, data, howmany=2):
        fuzzed = ''
        additional = ''
        for _ in xrange(howmany):
            additional += '%c' % (random.randint(0, 0xFF))

        index = random.randint(0, len(data))

        fuzzed = data[:index]
        fuzzed += additional
        fuzzed += data[index:]

        return fuzzed


class NullMutator(Mutator):
    '''
        Does absolutely nothing.
    '''
    def __init__(self):
        super(NullMutator, self).__init__()
