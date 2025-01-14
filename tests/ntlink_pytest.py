"""Tests for ntLink"""

import shlex
import subprocess
import re

def cleanup_files(file_list):
    "Remove all files in the input list"
    subprocess.call("ls")
    for out_file in file_list:
        command = "rm {0}".format(out_file)
        command_shlex = shlex.split(command)
        return_code = subprocess.call(command_shlex)
        assert return_code == 0

def test_1():
    "Testing two sequences together, long reads in fasta format"
    command = "../ntLink scaffold -B target=scaffolds_1.fa reads=long_reads_1.fa prefix=test1 k=32 w=250 z=500 n=2"
    command_shlex = shlex.split(command)
    return_code = subprocess.call(command_shlex)
    assert return_code == 0

    test_paths = []
    with open("test1.stitch.path", 'r') as test1_path:
        for line in test1_path:
            line = line.strip().split("\t")
            test_paths.append(line[1])

    expected_paths = ["188266+ 4529N 189231-", "189231+ 4529N 188266-"]
    for path in test_paths:
        assert path in expected_paths

    # Clean-up files
    files_to_delete = ["scaffolds_1.fa.k32.w250.z500.stitch.abyss-scaffold.fa", "scaffolds_1.fa.k32.w250.tsv",
                       "test1.pairs.tsv",
                       "test1.n2.scaffold.dot", "test1.stitch.path"]
    cleanup_files(files_to_delete)


def test_2():
    "Testing 4 sequences together, long reads in gzipped fastq format"
    command = "../ntLink scaffold -B target=scaffolds_2.fa reads=long_reads_2.fq.gz prefix=test2 w=100 k=32 z=500 n=2"
    command_shlex = shlex.split(command)
    return_code = subprocess.call(command_shlex)
    assert return_code == 0

    test_paths = []
    with open("test2.stitch.path", 'r') as test1_path:
        for line in test1_path:
            line = line.strip().split("\t")
            test_paths.append(line[1])

    expected_paths = ["189459+ 73N 183836- 448N 182169- 1311N 190964+", "190964- 1311N 182169+ 448N 183836+ 73N 189459-"]
    for path in test_paths:
        assert path in expected_paths

    # Clean-up files
    files_to_delete = ["scaffolds_2.fa.k32.w100.z500.stitch.abyss-scaffold.fa", "scaffolds_2.fa.k32.w100.tsv",
                       "test2.pairs.tsv",
                       "test2.n2.scaffold.dot", "test2.stitch.path"]
    cleanup_files(files_to_delete)

def test_3():
    "Testing multiple output paths, long reads in gzipped fasta format"
    command = "../ntLink scaffold -B target=scaffolds_3.fa reads=long_reads_3.fa.gz prefix=test3 k=24 w=250 z=500 n=2"
    command_shlex = shlex.split(command)
    return_code = subprocess.call(command_shlex)
    assert return_code == 0

    test_paths = []
    with open("test3.stitch.path", 'r') as test1_path:
        for line in test1_path:
            line = line.strip().split("\t")
            test_paths.append(line[1])

    expected_paths = ["189459+ 77N 183836- 434N 182169- 1294N 190964+", "190964- 1294N 182169+ 434N 183836+ 77N 189459-",
                      "188266+ 4566N 189231-", "189231+ 4566N 188266-"]
    for path in test_paths:
        assert path in expected_paths

    # Clean-up files
    files_to_delete = ["scaffolds_3.fa.k24.w250.z500.stitch.abyss-scaffold.fa",
                       "scaffolds_3.fa.k24.w250.tsv", "test3.pairs.tsv",
                       "test3.n2.scaffold.dot", "test3.stitch.path"]
    cleanup_files(files_to_delete)