# -*- coding: utf8 -*-

from __future__ import absolute_import
from __future__ import division, print_function, unicode_literals

import math
try:
    import numpy
except ImportError:
    numpy = None

try:
    from scipy.linalg import svd as singular_value_decomposition
except ImportError:
    singular_value_decomposition = None
from ._summarizer import AbstractSummarizer


class LsaSummarizer(AbstractSummarizer):
    MIN_DIMENSIONS = 3
    REDUCTION_RATIO = 1/1
    _stop_words = frozenset()

    @property
    def stop_words(self):
        return self._stop_words

    @stop_words.setter
    def stop_words(self, words):
        self._stop_words = frozenset(map(self.normalize_word, words))

    def __call__(self, document, sentences_count):
        self._ensure_dependecies_installed()

        dictionary = self._create_dictionary(document)
        # empty document
        if not dictionary:
            return ()

        matrix = self._create_matrix(document, dictionary)
        matrix = self._compute_term_frequency(matrix)
        u, sigma, v = singular_value_decomposition(matrix, full_matrices=False)

        ranks = iter(self._compute_ranks(sigma, v))
        return self._get_best_sentences(document.sentences, sentences_count,
            lambda s: next(ranks))

    def _ensure_dependecies_installed(self):
        if numpy is None:
            raise ValueError("LSA summarizer requires NumPy & SciPy. Please, install them by command 'pip install numpy scipy'.")
        elif singular_value_decomposition is None:
            raise ValueError("LSA summarizer requires SciPy. Please, install it by command 'pip install scipy'.")

    def _create_dictionary(self, document):
        """Creates mapping key = word, value = row index"""
        words = document.words
        unique_words = frozenset(self.stem_word(w) for w in words
            if w not in self._stop_words)

        return dict((w, i) for i, w in enumerate(unique_words))

    def _create_matrix(self, document, dictionary):
        """
        Creates matrix of shape |unique words|×|sentences| where cells
        contains number of occurences of words (rows) in senteces (cols).
        """
        sentences = document.sentences

        # create matrix |unique words|×|sentences| filled with zeroes
        matrix = numpy.zeros((len(dictionary), len(sentences)))

        for col, sentence in enumerate(sentences):
            for word in map(self.stem_word, sentence.words):
                # only valid words is counted (not stop-words, ...)
                if word in dictionary:
                    row = dictionary[word]
                    matrix[row, col] += 1

        return matrix

    def _compute_term_frequency(self, matrix, smooth=0.4):
        assert 0.0 <= smooth < 1.0

        max_word_frequencies = numpy.max(matrix, axis=0)
        rows, cols = matrix.shape
        for row in range(rows):
            for col in range(cols):
                max_word_frequency = max_word_frequencies[col]
                if max_word_frequency != 0:
                    frequency = matrix[row, col]/max_word_frequency
                    matrix[row, col] = smooth + (1.0 - smooth)*frequency

        return matrix

    def _compute_ranks(self, sigma, v_matrix):
        assert len(sigma) == v_matrix.shape[1]

        dimensions = max(LsaSummarizer.MIN_DIMENSIONS,
            int(len(sigma)*LsaSummarizer.REDUCTION_RATIO))
        powered_sigma = tuple(s**2 if i < dimensions else 0.0
            for i, s in enumerate(sigma))

        ranks = []
        # iterate over columns of matrix (rows of transposed matrix)
        for column_vector in v_matrix.T:
            rank = sum(s*v**2 for s, v in zip(powered_sigma, column_vector))
            ranks.append(math.sqrt(rank))

        return ranks
