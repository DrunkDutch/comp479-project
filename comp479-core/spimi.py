import core
import sys
import os
import datetime
import argparse
import cPickle as pickle


class Inverter:
    def __init__(self, tokens, block_prefix="bl_", block_size=100, block_index=0, out_dir="./blockfiles", senti_loc="senti.pk1"):
        self.tokens = iter(tokens)
        self.block_prefix = block_prefix
        self.block_size = block_size  # Max block size in MB to simulate memory restrictions
        self.block_index = block_index
        self.out_dir = out_dir
        self.blocklist = []
        self.get_out_dir()
        self.sentiments = pickle.load(open(senti_loc, 'rb'))

    def get_out_dir(self):
        """
        Creates output directory for inverted block files
        :return:
        """
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

    def index(self):
        """
        Method to actual index the corpus using the SPIMI algorithm
        Compresses dictionary depending on parameters passed in class constructor
        Writes blocks to inverted block files in output directory
        :return:
        """
        done = False
        while not done:
            block_dict = {}
            try:
                while sys.getsizeof(block_dict) / 1024 / 1024 <= self.block_size:
                    token = self.tokens.next()
                    if token[0] in self.sentiments:
                        score = self.sentiments[token[0]]
                    else:
                        score = 0
                    term = core.Term(token[0], score)
                    if term not in block_dict:
                        block_dict[term] = list()
                        block_dict[term].append(token[1])
                    else:
                        block_dict[term].append(token[1])
            except StopIteration:
                print "Parsed all tokens in all documents"
                done = True

            sorted_block = [termi for termi in sorted(block_dict.keys())]
            block_name = self.block_prefix + str(self.block_index) + ".txt"
            outFile = core.BlockFile(os.path.join(self.out_dir, block_name))
            outFile.open_file(mode="w")
            for element in sorted_block:
                docids = " ".join(str(doc) for doc in block_dict[element])
                outString = str(element) + " " + docids
                outFile.write_line(outString + "\n")
            outFile.close_file()
            self.block_index += 1
            self.blocklist.append(os.path.join(self.out_dir, block_name))


class Merger:
    def __init__(self, blockfiles, file_name="mf.txt", out_dir="./merged"):
        self.file_name = file_name
        self.out_dir = out_dir
        self.block_files = blockfiles
        self.get_out_dir()
        self.prep_output()
        self.out_file = core.BlockFile(os.path.join(self.out_dir, self.file_name))

    def prep_files(self):
        """
        Reads all inverted block files to prepare for merger function
        :return: List of open File classes for block files
        """
        open_files = []
        for out_file in self.block_files:
            open_files.append(core.BlockFile(out_file))
        return open_files

    def prep_output(self):
        """
        Deletes merged index file if it already exists in the the output folder
        :return:
        """
        try:
            os.remove(os.path.join(self.out_dir, self.file_name))
        except Exception:
            print "Could not find file to delete"
            pass

    def get_out_dir(self):
        """
        Creates output directory for inverted block files
        :return:
        """
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

    def merge(self):
        """
        Merger function to create an ordered index file from all the block files that were created to simulate memory restrictions
        Reads a single line from each file to ensure that actual memory is not exceeded
        :return:
        """
        in_files = [f.open_file() for f in self.prep_files()]
        next_lines = [f.read_line() for f in in_files]
        self.out_file.open_file(mode="w")
        while next_lines:
            next_term = core.BlockLine(list(), None, list())
            for index, line in enumerate(next_lines):
                line_obj = line
                line_obj.indexes = [index]
                if next_term.term is None:
                    next_term = line_obj
                elif line_obj.term == next_term.term:
                    next_term = line_obj.merge(next_term)
                elif line_obj.term < next_term.term:
                    next_term = line_obj

            self.out_file.write_line(next_term)
            new_indexes = next_term.indexes
            new_next_lines = [in_files[index].read_line() for index in new_indexes]
            offset = 0  # Create offset for indexes for when looping over the new lines read to ensure that indexes are aligned after deletion
            for index, new_line in enumerate(new_next_lines):
                try:
                    if new_line is None:
                        """
                        Remove block file that is at EOF
                        """
                        del(next_lines[new_indexes[index-offset]])
                        print "Closing file " + str(in_files[new_indexes[index-offset]])
                        in_files[new_indexes[index-offset]].close_file()
                        del(in_files[new_indexes[index-offset]])
                        offset += 1
                    else:
                        next_lines[new_indexes[index-offset]] = new_line
                except IndexError:
                    print "{} EXCEPTION with size {}".format(new_line, len(next_lines))
                    continue
        self.out_file.close_file()
        for f in in_files:
            try:
                f.close_file()
            except Exception:
                continue

        print "Finished merging files"


def get_command_line(argv=None):
    program_name = os.path.basename(sys.argv[0])
    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--digits", action="store_true", help="Enable digit removal dictionary compression")
        parser.add_argument("-c", "--case", action="store_true", help="Enable case folding dictionary compression")
        parser.add_argument("-s", "--stopwords", action="store_true", help="Enable stopword removal dictionary compression")
        parser.add_argument("-m", "--stemmer", action="store_true", help="Enable Porter Stemmer usage for dictionary compression")
        parser.add_argument("-S", "--size", type=int, help="Block size in MB to simulate memory restrictions")
        arguments = parser.parse_args(argv)
        return arguments

    except Exception as e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + " for help use --help")
        return None


if __name__ == "__main__":
    now = datetime.datetime.now()
    options = get_command_line()
    # print os.listdir("./blockfiles")
    # bfiles = [os.path.join("./blockfiles", file) for file in sorted(os.listdir("./blockfiles"))]
    corp = core.Corpus("./../Corpus", case=options.case, digits=options.digits, stem=options.stemmer, stop=options.stopwords)
    print corp.get_count()
    invert = Inverter(corp.tokens, block_size=options.size)
    invert.index()
    merger = Merger(invert.blocklist)
    merger.merge()
    print datetime.datetime.now() - now

