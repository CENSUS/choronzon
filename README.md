# Choronzon - An evolutionary knowledge-based fuzzer

## Introduction

This document aims to explain in brief the theory behind **Choronzon**.
Moreover, it provides details about its internals and how one can extend
**Choronzon** to meet new requirements. An overview of the architecture of
**Choronzon** was initially presented at the [ZeroNights 2015
Conference](http://2015.zeronights.org/). A
[recording](https://www.youtube.com/watch?v=WafsYOCl8hQ) of the presentation and
the [slide deck](https://census-labs.com/media/choronzon-zeronights-2015.pdf)
are also available.

**Choronzon** is an evolutionary fuzzer. It tries to imitate the evolutionary
process in order to keep producing better results. To achieve this,
it has an evaluation system to classify which of the fuzzed files are
interesting and which should be dropped.

Moreover, **Choronzon** is a knowledge-based fuzzer. It uses user-defined
information to read and write files of the targeted file format. To become
familiar with **Choronzon's** terminology, you should consider that each file is
represented by a **chromosome**. Users should describe the elementary structure
of the file format under consideration. A high level overview of the file format
is preferred instead of describing every detail and aspect of it. Each one of
those user-defined elementary structures is considered a **gene**. Each
chromosome contains a tree of genes and it is able to build the corresponding
file from it.

**Choronzon** is divided into three subsystems, the **Tracer** module,
the **Chromosome** module and the fuzzer.

Briefly, the **Chromosome** component is used to describe the target file
format. Users are able to write their own modules to support new or
custom formats. As a test-case, a PNG module is provided with **Choronzon**.

On the other hand, the **Tracer** component is responsible to monitor the target
application and collect various information about its execution. This version
of **Choronzon** uses [Intel's
Pin](https://software.intel.com/en-us/articles/pin-a-dynamic-binary-instrumentation-tool)
binary instrumentation tool in order to log the basic blocks that were visited
during the execution. However, **Choronzon** is able to support other tracing
backends as well. Also keep in mind that in the next version of Choronzon, Pin is
going to be replaced due to its staggering performance impact.

Lastly, the fuzzer component is used to alter the contents of the files to be
tested. The module contains a corpus of **Mutators** and **Recombinators**.
**Mutators**, simply, are changing the file like common fuzzers do. For example,
they perform byte flipping, byte swapping, random byte mutation and so on. But
**Choronzon** has another feature that is not that common across fuzzers.
**Recombinators** are using the information about the structure of the file
format, provided by the **Chromosome** module, in order to perform intelligent
fuzzing.

## Chromosome

In the directory `chromosome/parsers` you can find the file `PNG.py`. This
Python module describes the PNG file format to the fuzzer. You may add your
custom modules for other file formats in this directory.

The fundamental idea behind the **Chromosome** subsystem is to convert the
initial seed files using a **Deserializer** into a tree of **Genes**. At some
point, the (fuzzed) **Genes** will be written into a file, using a
**Serializer**.

Consider that in **Choronzon** the aim of the parser module is to provide
*the elementary structure* of the file format, instead of
every minor detail. This will help the fuzzer to construct files that are
mostly sane, avoiding early exiting from the target application.
Additionally, this approach saves time, because describing every aspect
of the file format is time consuming and introduces significant development
overhead.

### How to write a custom parser

A new parser module must import:

* chromosome.gene.AbstractGene
* chromosome.serializer.BaseSerializer
* chromosome.deserializer.BaseDeserializer

and it must implement

* a **Gene** class derived from **chromosome.gene.AbstractGene**,
* a **Serializer** class derived from **chromosome.serializer.BaseSerializer**,
* and a **Deserializer** class derived from
**chromosome.deserializer.BaseDeserializer**.

In the example shipped with **Choronzon**, each **PNGGene** corresponds to a PNG
chunk. Generally, you may think of a **Gene** as an *elementary data structure*
of the target format. Each **Chromosome** is comprised from a tree of **Genes**,
and represents a unique file. Each **Gene** must be able to produce a byte string
that contains its data combined with the data of the lower **Genes** in the
tree.

The **PNGSerializer** must be able to produce (a mostly sane) file from when
a list of **Genes** is given to it. On the other hand, **PNGDeserializer** must
be a able to parse a *valid* file of the target format and deserialize it to a
tree of **Genes**.

Check `chromosome/parsers/PNG.py` for a commented example for the PNG format.

## Tracer

The **Tracer** module is used to disassemble the target application (and/or one
or more of its libraries). In this version of **Choronzon** this is achieved
with IDA. We used this approach because we can correlate any interesting
information from the fuzzing campaign with our IDBs. However, we may drop the
dependency on IDA in the near future in order to make **Choronzon** more
portable and accessible.

A file is tested against an application with the help of a Pin utility. In the
`analyzer/coverage` directory there's the source code of this Pin tool, which
injects hooks in the beginning of each basic block at the target application.
When the execution is finished, we correlate the basic block that was hit, with
the basic block from the binary. Thus, we're able to calculate metrics that are
valuable for us (coverage etc).

## Fuzzer

The **Fuzzer** component is using the **Chromosome** representation to fuzz a
file. As mentioned earlier, there are two fuzzing methods in **Choronzon**.

For the first method, **Choronzon** gets the content from one or more genes
and applies one of the **Mutators**. **Mutators** implement common but effective
fuzzing methods like random byte mutation, high bit set, byte swapping
and many more. You may also write your own custom mutators and add them in
`fuzzers/mutators.py`.

The second fuzzing method is called recombination. **Recombinators** are
used to change the structure of the file. Here's an example with the
PNG format.

PNG files are comprised by consecutive chunks that contain four fields,

* length,
* chunk's type,
* chunk's data,
* and a CRC.

Let's assume we have a PNG file that only has IHDR, IDAT and IEND chunks. Its
structure would look like the following:

    [ PNG signature ] [ IHDR ] [ IDAT ] [ IEND ]

Since **Choronzon** is aware of the basic structures (i.e the PNG chunks),
it is able to alter their sequence. After a successful recombination the fuzzed
PNG output file can look like this:

    [ PNG signature ] [ IDAT ] [ IHDR ] [ IEND ]

**Choronzon** contains many more recombination strategies that make it
able to cope even with complicated file formats.

## Installation

**Choronzon** has been tested with Python 2.7, Pin 3, IDA Pro 6.6 to 6.9,
on Ubuntu 16.04 LTS (Linux kernel 4.4) and Windows 10.

In order to run it you'll need to install the sortedcontainers Python package.
You may find it [here](https://pypi.python.org/pypi/sortedcontainers) or install
it via pip.

Moreover, **Choronzon** needs IDA Pro (actually, its terminal version). The
path of IDA Pro should be specified in your configuration file like this:

```
DisassemblerPath = 'C:\\Program Files (x86)\\IDA 6.6'
```

It has been tested successfully with IDA Pro 6.6, 6.7, 6.8 and 6.9.

**Choronzon's** coverage Pin tool is located at `analyzer/coverage` and must be
compiled. You may want to check Pin's documentation for details, or you can
perform the following steps:

1. Copy the `coverage.cpp` and `makefile.rules` file to
`/path/to/pin/source/tools/MyPinTool`
2. Run `make`. If you're on Windows you should run the Visual 
Studio command line, and use the `make` utility and its dependencies from
[Cygwin](https://www.cygwin.com/)
3. Copy back to `/path/to/choronzon/analysis/coverage` the newly created
`obj-intel64` directory (or `obj-ia32` for 32 bit systems)

## Configuration

In order to fuzz with **Choronzon**, you must provide a configuration
file. In the `settings` directory there is an example of **Choronzon's**
configuration.

