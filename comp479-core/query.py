import core
from core import SerialCorpus
import operator
import spimi
import os
import sys
import argparse
import nltk
import string
import datetime
from collections import defaultdict
from math import log10
import cPickle as pickle
import json


class QueryProcessor:
    """
    Wrapper class to handle query processing and result parsing
    """
    B_WEIGHT = 1.6
    K_WEIGHT = 0.75

    def __init__(self, query_type="AND", query_list=[], merge="./merged/mf.txt", corpus="./../Corpus", out_dir=" ./../output", digits=True, case=True, stop=True, stem=True, metacorp="corpus_pickle.pk1", sentiment="senti.pk1"):
        self.type = query_type
        self.terms = query_list
        self.merge = merge
        self.corpus = corpus
        self.out_dir = out_dir
        self.digits = digits
        self.case = case
        self.stop = stop
        self.stem = stem
        self.meta_info = SerialCorpus.load(metacorp)
        self.index = {}
        self.get_index()
        self.get_out_dir()
        self.terms = [self.clean(term) for term in self.terms]
        self.terms = [str(x) for x in self.terms if x is not None]
        self.sentiments = pickle.load(open(sentiment, "rb"))
        self.score = self.get_score()

    def get_score(self):
        score = 0
        for term in self.terms:
            if term in self.sentiments:
                score += self.sentiments[term]
        return score



    def clean(self, input):
        """
        Compresses query terms in manner similar to that used by the Corpus processor class @core.Document
        :param input:
        :return:
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

    def get_out_dir(self):
        """
        Prepares output directory (creates if doesn't exist, and empties if does exist)
        :return:  None
        """
        try:
            for f in os.listdir(self.out_dir):
                if f.endswith(".txt"):
                    os.remove(os.path.join(self.out_dir, f))
        except Exception:
            print "woops, Couldn't delete folders in output locations"
        if not os.path.exists(self.out_dir):
            try:
                os.makedirs(self.out_dir)
            except Exception:
                print "Folder already exists"


    def get_index(self):
        """
        Populates class with merged spimi index file to allow for in-memory querying
        :return:
        """
        in_file = core.BlockFile(self.merge)
        in_file.open_file()
        in_line = in_file.read_line()
        term = core.Term(in_line.term, in_line.score, in_line.df)
        while in_line:
            term = core.Term(in_line.term, in_line.score, in_line.df)
            self.index[term] = in_line.postings
            in_line = in_file.read_line()

    def and_query(self):
        postings = []
        doc_weight = {}
        idf_values = {}
        for index, term in enumerate(self.terms):
            try:
                postings.append(set(self.index[term]))
                idf_values[term] = self.get_idf(list(set(self.index[term])))
                document_list = set(self.index[term])
                for docId in sorted(document_list):
                    frequency = self.get_document_freq(str(term), docId)
                    if str(docId) not in doc_weight:
                        doc_weight[str(docId)] = self.calculate_score(idf_values[str(term)], frequency, docId)
                    else:
                        doc_weight[str(docId)] += self.calculate_score(idf_values[str(term)], frequency, docId)
            except KeyError:
                postings.append(set([]))
        intersection = set.intersection(*postings)
        returnDict = {}
        for key in doc_weight.keys():
            if int(key) in intersection:
                returnDict[key] = doc_weight[key]
        if self.score >= 0:
            return sorted(returnDict.items(), key=operator.itemgetter(1), reverse=True)
        else:
            return sorted(returnDict.items(), key=operator.itemgetter(1))

    def or_query(self):
        postings = []
        doc_weight = {}
        idf_values = {}
        sentiment_score = {}
        for index, termi in enumerate(self.terms):
            try:
                if termi in self.sentiments:
                    score = self.sentiments[termi]
                else:
                    score = 0
                term = core.Term(termi, score)
                print term
                postings.append(set(self.index[term]))
                idf_values[term] = self.get_idf(list(set(self.index[term])))
                document_list = set(self.index[term])
                for docId in sorted(document_list):
                    frequency = self.get_document_freq(term, docId)
                    if str(docId) not in doc_weight:
                        doc_score = self.calculate_score(idf_values[term], frequency, docId)
                        doc_weight[str(docId)] = doc_score
                    else:
                        doc_weight[str(docId)] += self.calculate_score(idf_values[term], frequency, docId)
            except KeyError:
                print "Key error"
                postings.append(set([]))
        union = set.union(*postings)
        returnDict = {}
        for key in doc_weight.keys():
            if int(key) in union:
                returnDict[key] = doc_weight[key]
        if self.score >= 0:
            return sorted(returnDict.items(), key=operator.itemgetter(1), reverse=True)
        else:
            return sorted(returnDict.items(), key=operator.itemgetter(1))

    def process_query(self):
        """
        Wrapper function to call the proper query function and outputs result articles to output_dir
        :return: List of result articleIds
        """
        print "Processing query for terms " + " ".join(self.terms)
        result_list = []
        if self.type is "AND":
            result_list = self.and_query()
        else:
            result_list = self.or_query()

        return self.get_articles(result_list)

    def get_articles(self, articles):
        """
        Prints out result articles to separate text files in output_dir for ease of usage
        :param articles: Set of docIds from query result
        :return: List of Articles
        """
        res_list = []
        for article in articles:
            score = article[1]
            article = int(article[0])
            corp_file = (article / 1000) + 1
            art_index = (article % 1000) - 1
            if corp_file < 10:
                file_name = "corpus" + str(corp_file) + ".json"
            else:
                file_name = "corpus" + str(corp_file) + ".json"
            with open(os.path.join(self.corpus, file_name), "r") as reut:
                data = json.load(reut)
            # doc_dump = core.Document.parse_tags("REUTERS", data, False)
            # for index, doc in enumerate(doc_dump):
            #     if index == art_index:
            print "Found result in article {} with score {}".format(article, score)
            with open(os.path.join(self.out_dir, str(article)+".txt"), "wb") as out_file:
                out_file.write("The document URL is: {}\n".format(data['url']))
                content = data['content']
                out_file.write(content.encode("UTF-8"))
            res_list.append(article)
        print len(res_list)
        return sorted(res_list)

    def get_idf(self, postings):
        return log10((self.meta_info.doc_count-len(postings)+0.5)/(len(postings)+0.5))

    def get_document_freq(self, term, docId):
        return self.index[term].count(docId)

    # Made it now return sentiment value * BM25 score to weight documents by score and sentiment
    def calculate_score(self, idf_score, frequency, docId):
        if self.meta_info.documents[docId][2] == 0:
            return idf_score * ((frequency*(QueryProcessor.K_WEIGHT+1))/(frequency+QueryProcessor.K_WEIGHT*(1-QueryProcessor.B_WEIGHT + QueryProcessor.B_WEIGHT*(self.meta_info.documents[docId][1]/self.meta_info.doc_length))))
        if self.meta_info.documents[docId][2] > 0:
            return (self.meta_info.documents[docId][2]+1) * (idf_score * ((frequency*(QueryProcessor.K_WEIGHT+1))/(frequency+QueryProcessor.K_WEIGHT*(1-QueryProcessor.B_WEIGHT + QueryProcessor.B_WEIGHT*(self.meta_info.documents[docId][1]/self.meta_info.doc_length)))))
        if self.meta_info.documents[docId][2] < 0:
            return (self.meta_info.documents[docId][2]-1) * (idf_score * ((frequency*(QueryProcessor.K_WEIGHT+1))/(frequency+QueryProcessor.K_WEIGHT*(1-QueryProcessor.B_WEIGHT + QueryProcessor.B_WEIGHT*(self.meta_info.documents[docId][1]/self.meta_info.doc_length)))))



def get_command_line(argv=None):
    program_name = os.path.basename(sys.argv[0])
    if argv is None:
        argv = sys.argv[1:]

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-a", "--AND",
                            help="Choose AND type query, if used with -o or --OR parameter, supercedes it",
                            action="store_true")
        parser.add_argument("-o", "--OR",
                            help="Choose OR type query, if used with -a or --AND parameter, is superceded by it",
                            action="store_true")
        parser.add_argument("-d", "--digits", action="store_true", help="Enable digit removal on query terms")
        parser.add_argument("-c", "--case", action="store_true", help="Enable case folding on query terms")
        parser.add_argument("-s", "--stopwords", action="store_true", help="Enable stopword removal on query terms")
        parser.add_argument("-m", "--stemmer", action="store_true", default=False,
                            help="Enable Porter Stemming on query terms")
        parser.add_argument("-q", "--query", help="Query Terms to search for, in the form \"TERM TERM\", with each term"
                                                  " separated by a space, and/or terms are not required unless they are"
                                                  " actual query terms")

        arguments = parser.parse_args(argv)
        return arguments
    except Exception as e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + " for help use --help")
        return None


if __name__ == __name__:
    now = datetime.datetime.now()
    options = get_command_line()
    query_type_in = "AND"
    if options.OR:
        query_type_in = "OR"
    if options.AND:
        query_type_in = "AND"
    if not options.AND and not options.OR:
        print "Please select a valid query type"
    q_list = options.query.split(" ")
    print q_list
    qp = QueryProcessor(query_type=query_type_in, query_list=q_list, digits=options.digits, case=options.case, stop=options.stopwords, stem=options.stemmer)
    print qp.score
    # print len(qp.index.keys())
    res = qp.process_query()


    print datetime.datetime.now() - now
