import nltk
import os
import re
import string
import cPickle as pickle
import datetime


class Corpus:
    """
    Wrapper class to handle the parsing of the corpus as a whole, also helps pass compression parameters to the Document
    class
    """
    def __init__(self, source, case=False, digits=False, stop=False, stem=False, sentiment="./../AFINN-111.txt"):
        self.path = source
        self.files = [os.path.join(self.path, file) for file in os.listdir(self.path) if file.endswith(".sgm")]
        self.case = case
        self.digits = digits
        self.stop = stop
        self.stem = stem
        self.sentiment_loc = sentiment
        self.sentiment = self.get_sentiment()
        self.documents = self.parse_documents()
        self.tokens = self.get_tokens()
        self.score = sum([document.score for document in self.documents])
        self.save()

    def get_sentiment(self):
        sent_list = {}
        with open(self.sentiment_loc, 'rb') as myfile:
            next_line = myfile.readline()
            while next_line:
                key = self.clean(next_line.split("\t")[0])
                score = int(next_line.split("\t")[1].strip())
                sent_list[key] = score
                next_line = myfile.readline()
        with open("senti.pk1", "wb") as dill:
            pickle.dump(sent_list, dill, pickle.HIGHEST_PROTOCOL)
        return sent_list


    def get_count(self):
        count = 0
        for doc in self.documents:
            count += doc.count
        return count

    def get_tokens(self):
        tokens = []
        for doc in self.documents:
            tokens.extend(doc.tokens)
        return tokens

    def parse_documents(self):
        """
        Iterates over the files in the corpus folder to parse and generate postings pairs
        :return: List of parsed file objects
        """
        doc = []
        for file in self.files:
            print "Currently parsing articles from file {}", file
            with open(file, 'rb') as myfile:
                data = myfile.read()
            for article in Document.parse_tags("REUTERS", data, False):
                    doc.append(Document(article, case=self.case, digits=self.digits, stem=self.stem, stop=self.stop, sentiments=self.sentiment))
        return doc

    def save(self):
        num_documents = len(self.documents)
        num_tokens = self.get_count()
        doc_length = float(num_tokens/num_documents)
        pickle_corpus = SerialCorpus(num_documents, num_tokens, doc_length, self.documents, self.score)
        pickle_corpus.save()
        corp = SerialCorpus.load("corpus_pickle.pk1")
        print corp

    def clean(self, input):
        """
        Allows for compression of dictionary based on the parameters passed at construction
        Options are:
        Digit removal
        Case Folding
        Stopword removal
        Porter Stemming
        :param input: Word to be compressed
        :return: Compressed Word
        """
        output = input
        if self.digits:
            for s in output:
                if s.isdigit():
                    return None
        if self.case:
            output = output.lower()
        if self.stop:
            punctuation = [str(x) for x in string.punctuation]
            stops = set(nltk.corpus.stopwords.words('english') + punctuation)
            if output in stops:
                return None
        if self.stem:
            stemmer = nltk.PorterStemmer()
            output = stemmer.stem(output)
        return str(output)


class SerialCorpus:
    """
    Data class written to handle serialization of the Corpus class. Created due to issues found when trying to pickle
    the original Corpus class
    """
    def __init__(self, num_documents=0, num_tokens=0, doc_length=0.0, documents=[], score=0):
        self.doc_count = num_documents
        self.token_count = num_tokens
        self.doc_length = float(doc_length)
        self.documents = dict()
        self.populate(documents)
        self.score = score

    def populate(self, documents):
        for doc in documents:
            self.documents[doc.id] = (doc.id, doc.count, doc.score)

    def save(self):
        with open("corpus_pickle.pk1", 'wb') as dill:
            pickle.dump(self, dill, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, fileIn):
        load = pickle.load(open(fileIn, 'rb'))
        return load

    def __str__(self):
        return "Number of Documents = " + str(self.doc_count) + "\n" + "Number of Tokens = " + str(self.token_count) + "\n" + "Average Document length = " + str(self.doc_length)


class Document:

    def __init__(self, source, case=True, digits=True, stop=True, stem=True, sentiments={}):
        self.raw = self.parse_tags("REUTERS", source, False)[0]
        self.id = self.get_id()
        self.topics_places = self.parse_tags("D", self.raw)
        self.text = self.parse_tags("TEXT", self.raw, False)[0]
        self.title = self.parse_tags("TITLE", self.text)[0]
        self.dateline = self.parse_tags("DATELINE", self.text)[0]
        self.body = self.get_body()
        self.sentiments = sentiments
        self.case = case
        self.digits = digits
        self.stop = stop
        self.stem = stem
        self.count = 0
        self.score = 0
        self.tokens = self.tokenize()


    @staticmethod
    def parse_tags(tag, source, strict=True):
        """
        Parser function to find the information contained within the desired tags
        Strips the tags from strict calls, but retains during non-strict due to regex restrictions
        on wildcard characters in look-ahead/behind structures
        """
        results = []
        try:
            if strict:
                body_regex = re.compile('(?<=\<'+tag+'>).*?(?=\</'+tag+'>)', flags=re.DOTALL)
            else:
                body_regex = re.compile('<' + tag + '.*?>.*?</' + tag + '>', flags=re.DOTALL)
            results = re.findall(body_regex, source)
            if len(results) is 0:
                results = [""]
        except IndexError:
            results = [""]
        finally:
            return results

    def get_id(self):
        regex = re.compile("(?<=NEWID=\")\d+")
        result = re.findall(regex, self.raw)
        return result[0]

    def get_body(self):
        """
        Parser function to return the actual body of the text, stripping away all metadata and tags
        """
        if self.text.find("<BODY>") != -1:
            return self.text.split("</DATELINE>")[1].split("</BODY>")[0].replace("<BODY>", '')
        if self.text.find("<DATELINE>") != -1:
            return self.text.split("</DATELINE>")[1].split("</TEXT>")[0]
        if self.text.find("<TITLE>") != -1:
            return self.text.split("</TITLE>")[1].split("</TEXT>")[0]
        else:
            return self.text.split("</TEXT>")[0]

    def clean(self, input):
        """
        Allows for compression of dictionary based on the parameters passed at construction
        Options are:
        Digit removal
        Case Folding
        Stopword removal
        Porter Stemming
        :param input: Word to be compressed
        :return: Compressed Word
        """
        output = input
        if self.digits:
            for s in output:
                if s.isdigit():
                    return None
        if self.case:
            output = output.lower()
        if self.stop:
            punctuation = [str(x) for x in string.punctuation]
            stops = set(nltk.corpus.stopwords.words('english') + punctuation)
            if output in stops:
                return None
        if self.stem:
            stemmer = nltk.PorterStemmer()
            output = stemmer.stem(output)
        return str(output)

    def tokenize(self):
        """
        Parse the raw document and returns the postings for each token
        Also provides a total count of all tokens found in the document
        :return: List of postings in the document
        """
        token_list = []
        text = [self.body, self.title]
        text.extend(self.topics_places)
        text = self.body + self.title
        word_list = nltk.word_tokenize(text)
        for word in word_list:
            try:
                word = str(word)
                stemmed_word = self.clean(word)
                if stemmed_word is None:
                    continue
                token_list.append((stemmed_word, self.id))
                self.count += 1
                if stemmed_word in self.sentiments:
                    self.score += self.sentiments[stemmed_word]
            except UnicodeDecodeError:
                token_list.append((word.split(".")[0], self.id))
                self.count += 1
        cleaned = token_list
        return cleaned


class BlockLine:
    """
    Wrapper class to facilitate each line in the block files
    Without this was causing many issues in regards to merging and variable handling for index movement
    Wraps the docIds associated with a term, term itself and index of blockfile in list of blockfiles
    """
    def __init__(self, indexes, term, postings, score=0):
        self.indexes = indexes
        self.term = term
        self.postings = postings
        self.score = score
        self.df = len(set(self.postings))

    @classmethod
    def from_line_entry(cls, indexes, line):
        """
        Alternative constructor from string
        :param indexes: file indexes
        :param line: raw line from block file
        :return: BlockLine class instance
        """
        split_line = line.split(" ")
        return cls(indexes, split_line[0], [int(doc_id) for doc_id in split_line[2:]], score=split_line[1])

    def merge(self, other_bl):
        """
        Merge 2 unique objects
        :param other_bl: Other BlockLine object
        :return: Merged instance
        """
        new_indexes = list(sorted(self.indexes + other_bl.indexes))
        new_postings = list(set(sorted(self.postings + other_bl.postings)))
        return BlockLine(new_indexes, self.term, new_postings, self.score)

    def __str__(self):
        return "{} {} {}\n".format(self.term, self.score, " ".join([str(doc_id) for doc_id in self.postings]))


class BlockFile:
    """
    Wrapper class to handle file actions for Block classes created by the SPIMI inverter
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_handle = None
        self.term_count = 0

    def open_file(self, mode='r'):
        self.file_handle = open(self.file_path, mode)
        return self

    def write_line(self, line_obj):
        self.file_handle.write(str(line_obj))
        self.term_count += 1

    def read_line(self):
        line_string = self.file_handle.readline()
        if line_string:
            return BlockLine.from_line_entry(-1, line_string)
        else:
            return None

    def close_file(self):
        self.file_handle.close()

    def __str__(self):
        return str(self.file_path)


class Term:
    def __init__(self, term, score, freq=0):
        self.term = str(term)
        self.score = score
        self.freq = freq

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.term == other.term
        return False

    def __hash__(self):
        return hash(self.term)

    def __cmp__(self, other):
        if hasattr(other, 'term'):
            return self.term == other.term

    def __repr__(self):
        return '{} {} {}'.format(self.term, self.score, self.freq)

    def __str__(self):
        return '{} {}'.format(self.term, self.score)


"""
Install punkt package from nltk to be able to tokenize english
install stopwords corpus for nltk to remove stopwords
"""

# TODO parse the sentiment analysis file into dictionary based on compression technique
if __name__ == "__main__":
    now = datetime.datetime.now()
    corp = SerialCorpus.load("corpus_pickle.pk1")
    print corp.documents['67']
    # corpus = Corpus("./../Corpus", digits=True, stop=True, case=True)
    # # print len(corpus.documents)
    # for index, doc in enumerate(corpus.documents):
    #     print index, doc.id
    print datetime.datetime.now() - now