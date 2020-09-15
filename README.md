# ntLink
Long read assembly scaffolder using minimizers

### Description of the algorithm
ntLink uses minimizers to perform a lightweight mapping between the input target assembly and the supplied long reads.

#### General steps in the algorithm:
1. Compute ordered minimizer sketches of the input assembly and long reads
2. Use minimizers to map long reads to the input assembly contigs, and use the information to output contig pairs
3. Scaffold the assembly using the contig pairing information using `abyss-scaffold`

### Credits
Concept: Rene Warren and Lauren Coombe

Design and implementation: Lauren Coombe

## Usage
```
ntLink: Scaffolding assemblies using long reads
ntLink v0.0.1
Usage: ntLink scaffold target=<target scaffolds> reads='List of long read files'

Options:
target			Target assembly to be scaffolded in fasta format
reads		        List of long read files (separated by a space)
prefix			Prefix of intermediate output files [out.k<k>.w<w>.n<n>]
t			Number of threads [4]
k			K-mer size for minimizers [32]
w			Window size for minimizers (bp) [250]
n			Minimum graph edge weight [2]
g			Minimum gap size (bp) [20]
f			Maximum number of contigs in a run for full transitive edge addition [10]
a                        Minimum number of anchored ONT reads required for an edge [1]
z			Minimum size of contig (bp) to scaffold [500]

Note: 
	- Ensure all assembly and read files are in the current working directory, making soft links if neccessary
```

Running `ntLink help` prints the help documentation.

* Input reads files can be gzipped (or not), and in either fastq or fasta format

#### Example
Input files:
* target assembly `my_assembly.fa`
* long read files `long_reads_1.fq.gz`, `long_reads_2.fq.gz`

ntLink command:
```
ntLink scaffold target=my_assembly.fa reads='long_reads_1.fq.gz long_reads_2.fq.gz k=32 w=500'
```
 ## Installation
 Installing from source code:
 ```
git clone https://github.com/bcgsc/ntLink.git
cd src
make
```

## Dependencies
* Python3 ()
* [ABySS](https://github.com/bcgsc/abyss)