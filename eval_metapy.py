import metapy
from base_helpers import *
import math

# Compute IDF weighting
def idf(term_id, idx_train):
    return math.log((idx_train.num_docs() + 1)/(idx_train.doc_freq(term_id)),2)


# Custom BM25 ranker to compute the rank score of one doc for one query.
# document: tuple in the form (doc_id_test, analyzed_doc)
# doc_id_test: document id in the test set
# analyzed_doc: a dict generated by metapy analyzer through fitlering and tokenization in the form {term: freq}
# analyzed_query: query that has been filtered and tokenized into a dict of {term: freq}
# idx_test: inverted index for the test set
# idx_train: inverted index for the training set
# k: TF weighting parameter, between 0 and inf.
# b: Length normalization influence, between 0 and 1.
def BM25_score(document, analyzed_query, idx_test, idx_train, k, b):
    rank_score = 0
    # Current document length
    doc_length = 0
    analyzed_doc = document[1]
    for term in analyzed_doc:
        doc_length += analyzed_doc[term]

    # Compute rank score by summing over all shared terms.
    for term in analyzed_query:
        # Check if doc also contains term first. Otherwise skip.
        if (term not in analyzed_doc):
            continue

        # Term count for the query
        c_w_q = analyzed_query[term]
        # Term id in the test set containing the document
        term_id_test = idx_test.get_term_id(term)
        # Term id in the training set
        term_id_train = idx_train.get_term_id(term)
        # Document test set id.
        doc_id_test = document[0]
        # Compute average document length in the training set after adding current doc to it.
        avdl = (idx_train.avg_doc_length()*idx_train.num_docs() + doc_length)/(idx_train.num_docs() + 1)
        c_w_d = idx_test.term_freq(term_id_test, doc_id_test)
        rank_score += c_w_q*c_w_d*(k+1)/(c_w_d + k*(1 - b + b*doc_length/avdl))*idf(term_id_train,idx_train)

    return rank_score


# Given a list of gains from the top retrieved documents, compute DCG sum.
def ndcg_helper(list_gains):
    # compute numerator
    sum = 0
    for i in range(1, len(list_gains) + 1):
        # i = index + 1
        if i == 1:
            sum += list_gains[i-1]
        else:
            sum += list_gains[i-1]/math.log(i,2)

    return sum


# qID: query ID
# retrieved_docs: list of tuples in the form [(docID, gain),...] in the order of retrieved rank (top to bottom) for the
# current qID. Note that docID here corresponds to the original docID if dataset is split from a larger set.
# qrel_dict: dictionary containing all query relevance information from the test set in the format {qID: {docID: gain}}
# all_docIDs: all the (original) docIDs included in the test set
# NDCG is cutoff at len(retrieved_docIDs)
def ndcg(qID, retrieved_docs, qrel_dict, all_docIDs):
    result = 0
    if qID in qrel_dict: # qrel_dict contains relevance information about this query
        # Parse the query relevance file and compute the max DCG.
        all_gains = []
        n = len(retrieved_docs) # cutoff number
        for docID in all_docIDs:
            if docID in qrel_dict[qID]:
                all_gains.append(qrel_dict[qID][docID])

        # Compute max DCG
        all_gains.sort(reverse=True)
        denom = ndcg_helper(all_gains[0:n])
        retrieved_gains = [tuple[1] for tuple in retrieved_docs]
        numerator = ndcg_helper(retrieved_gains)

        if denom > 0:
            result = numerator/denom

    return result

