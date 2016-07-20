#!/usr/bin/env python

'''
    this script is meant to be run inside IDA Pro,
    as an IDAPython script.
'''

import os
import idc
import idaapi

def find_functions():
    '''
        yields all functions in the form a 2-tuple:

            (function_address, function_name)

        function_address is a RELATIVE offset from the
        image base.
    '''
    # get image base from IDA
    image_base = idaapi.get_imagebase()

    # iterate through all functions in the executable.
    for func_ea in Functions(MinEA(), MaxEA()):
        # craft the routine record
        func_name = GetFunctionName(func_ea)
        funcaddr = func_ea - image_base
        yield funcaddr, func_name

def find_bbls(function_ea):
    '''
        yields all basic blocks that belong to the
        given function. The blocks are returned in
        a 2-tuple like:

            (start_address, end_address)

        Both start and end address are RELATIVE offsets
        from the image base.
    '''

    # get image base from IDA
    image_base = idaapi.get_imagebase()
    function_ea += image_base

    # get flow chart from IDA
    flow_chart = idaapi.FlowChart(
            idaapi.get_func(function_ea),
            flags=idaapi.FC_PREDS
            )

    # iterate through all basic blocks in
    # the current routine
    for block in flow_chart:
        start_addr = block.startEA - image_base
        end_addr = block.endEA - image_base
        if start_addr != end_addr:
            yield start_addr, end_addr

def write(stream, msg):
    stream.write('%s\n' % msg)
    stream.flush()

def get_image():
    name = idc.GetInputFile()
    base = idaapi.get_imagebase()
    return base, name

def dump_all(output):
    with open(output, 'w') as fout:
        print '[+] Dumping image...'
        write(fout, '##IMAGE##')
        base, name = get_image()
        write(fout, '%s,%s' % (base, name))

        print '[+] Dumping all functions...'
        write(fout, '##FUNCTIONS##')
        functions = find_functions()
        for fea, fname in functions:
            write(fout, '%s,%s' % (fea, fname))

        print '[+] Dumping all basic blocks...'
        write(fout, '##BBLS##')
        functions = find_functions()
        for fea, fname in functions:
            for start, end in find_bbls(fea):
                write(
                        fout, '0x%x,0x%x,%s' % (
                            start,
                            end,
                            fname
                            )
                        )

def wait_until_ready():
    '''
        first thing you should wait until IDA has parsed
        the executable.
    '''
    print "[+] Waiting for auto-analysis to finish..."
    # wait for the autoanalysis to finish
    idc.Wait()

def prepare_output(path):
    idb_name = os.path.basename('%s.idmp' % idc.GetInputFile())
    path = os.path.abspath(path)
    return os.path.join(path, idb_name)

def dump(path):
    out = prepare_output(path)
    wait_until_ready()
    print '[+] Dumping everything on: %s' % out
    dump_all(out)

def main(args):
    dump(args.output)
    return 0

if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="a tool that analyzes an executable file or \
                an .idb/.i64 and dumps everything on a file."
        )

    parser.add_argument(
        "-o",
        "--output",
        help='the directory to save the output file, default is /tmp/.',
        default="/tmp/"
        )

    args = parser.parse_args(idc.ARGV[1:])

    sys.exit(main(args))
