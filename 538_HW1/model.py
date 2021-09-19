"""
author-gh: @adithya8
editor-gh: ykl7
"""

import math

import numpy as np
import torch
import torch.nn as nn

sigmoid = lambda x: 1 / (1 + torch.exp(-x))


class WordVec(nn.Module):
    def __init__(self, V, embedding_dim, loss_func, counts):
        super(WordVec, self).__init__()
        self.center_embeddings = nn.Embedding(num_embeddings=V, embedding_dim=embedding_dim)
        self.center_embeddings.weight.data.normal_(mean=0, std=1 / math.sqrt(embedding_dim))
        self.center_embeddings.weight.data[self.center_embeddings.weight.data < -1] = -1
        self.center_embeddings.weight.data[self.center_embeddings.weight.data > 1] = 1

        self.context_embeddings = nn.Embedding(num_embeddings=V, embedding_dim=embedding_dim)
        self.context_embeddings.weight.data.normal_(mean=0, std=1 / math.sqrt(embedding_dim))
        self.context_embeddings.weight.data[self.context_embeddings.weight.data < -1] = -1 + 1e-10
        self.context_embeddings.weight.data[self.context_embeddings.weight.data > 1] = 1 - 1e-10

        self.loss_func = loss_func
        self.counts = counts

    def forward(self, center_word, context_word):

        if self.loss_func == "nll":
            return self.negative_log_likelihood_loss(center_word, context_word)
        elif self.loss_func == "neg":
            return self.negative_sampling(center_word, context_word)
        else:
            raise Exception("No implementation found for %s" % (self.loss_func))

    def negative_log_likelihood_loss(self, center_word, context_word):
        ### TODO(students): start
        center_embeds = self.center_embeddings(center_word)
        context_embeds = self.context_embeddings(context_word)
        mul = context_embeds.mul(center_embeds).sum(-1)
        log_sum_exp = torch.log(torch.exp(mul).sum())  # log \sum{ exp(u_o^T v_c) }
        loss = torch.sum(log_sum_exp.subtract(mul))  # \sum {log_sum_exp - u_o^T v_c}
        ### TODO(students): end

        return loss

    def negative_sampling(self, center_word, context_word):
        ### TODO(students): start
        center_embeds = self.center_embeddings(center_word)
        context_embeds = self.context_embeddings(context_word)
        mul = context_embeds.mul(center_embeds).sum(-1)
        positive_los = torch.log(sigmoid(mul)).sum()

        positive_sample = []  # construct positive samples for negative sample checking
        center_arr = center_word.numpy()
        context_arr = context_word.numpy()
        for i, x in enumerate(center_arr):
            positive_sample.append((x, context_arr[i]))

        word_freq = []
        freq_sum = 0
        for i, cnt in enumerate(self.counts):
            word_freq[i] = cnt ** (3 / 4)  # adjust count according to the paper
            freq_sum += word_freq[i]
        for i, freq in enumerate(word_freq):  # calculate adjusted frequencies
            word_freq[i] = freq / freq_sum

        sample_size = len(center_word)
        cur_size = 0
        neg_context_arr = []
        while cur_size < sample_size:
            center = center_arr[cur_size]  # use the same center word
            random_context = np.random.choice(range(len(word_freq)), p=word_freq)  # pick a context word
            if (center, random_context) in positive_sample:  # chosen sample exists
                continue
            neg_context_arr.append(random_context)
            cur_size += 1

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        neg_center = torch.LongTensor(np.array(center_arr, dtype=np.int32)).to(device)
        neg_context = torch.LongTensor(np.array(neg_context_arr, dtype=np.int32)).to(device)
        neg_center_embeds = self.center_embeddings(neg_center)
        neg_context_embeds = self.context_embeddings(neg_context)
        neg_mul = neg_context_embeds.mul(neg_center_embeds).sum(-1)
        neg_los = torch.log(sigmoid(neg_mul)).sum()

        loss = -(positive_los + neg_los)
        ### TODO(students): end

        return loss

    def print_closest(self, validation_words, reverse_dictionary, top_k=8):
        print('Printing closest words')
        embeddings = torch.zeros(self.center_embeddings.weight.shape).copy_(self.center_embeddings.weight)
        embeddings = embeddings.data.cpu().numpy()

        validation_ids = validation_words
        norm = np.sqrt(np.sum(np.square(embeddings), axis=1, keepdims=True))
        normalized_embeddings = embeddings / norm
        validation_embeddings = normalized_embeddings[validation_ids]
        similarity = np.matmul(validation_embeddings, normalized_embeddings.T)
        for i in range(len(validation_ids)):
            word = reverse_dictionary[validation_words[i]]
            nearest = (-similarity[i, :]).argsort()[1:top_k + 1]
            print(word, [reverse_dictionary[nearest[k]] for k in range(top_k)])
