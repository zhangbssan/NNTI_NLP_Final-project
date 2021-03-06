# -*- coding: utf-8 -*-
"""MODEL.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1CHgUtO3SFNHvPfxZ7Lw_-ZGCTTgUzCps
"""

# Imports
import torch
torch.manual_seed(10)
from torch.autograd import Variable
import pandas as pd
import numpy as np
import sklearn as sk
import matplotlib.pyplot as plt
import re
import warnings
warnings.filterwarnings("ignore")
from matplotlib import pyplot as plt
import nltk
import torch.nn as  nn
import torch.optim as optim
import torch.nn.functional as F

"""Build the vocabulary"""

def vocabulary(data):
  V = {}
  i=0
  for s in range(len(data)):
    n=data[s]
    for y in range(len(n)):
      w=data[s][y]
      if w not in V:
        V[w] = i
        i+=1
      y+=1
    s+=1
  return V

"""Skip-Gram"""

def get_target_context(sentence):
    word_lists=[]
    for i in range(len(sentence)):
       w=sentence[i]
       for n in range(2):
                # look back
          if (i-n-1)>=0:
            word_lists.append([w] + [sentence[i-n-1]])
                
                # look forward
          if (i+n+1)<len(sentence):
            word_lists.append([w]+[sentence[i+n+1]])
    return word_lists
    pass

""" Pytorch Module"""

embedding_size = 64
vocabulary_size=4669 # for Bengali
vocabulary_size1=11137 # for Hindi

class Word2Vec(nn.Module):
    
    def __init__(self, embed_size, vocab_size):
        super(Word2Vec, self).__init__()
        self.input = nn.Embedding(vocab_size, embedding_size)
        self.output = nn.Linear(embedding_size, vocab_size,bias=False)


    def forward(self, one_hot):
        #one_hot = torch.tensor(one_hot）
        
        emb = self.input(one_hot)
        hidden = self.output(emb)
        out = F.log_softmax(hidden)
        return out

EMBEDDING_DIM = embedding_size 
N_FILTERS = 100
FILTER_SIZES = [2,3,4]
OUTPUT_DIM = 1
DROPOUT = 0.5

class CNN(nn.Module):
    def __init__(self, embedding_dim, n_filters, filter_sizes, output_dim, 
                 dropout):
        
        super().__init__()
        
       # self.embedding = nn.Embedding(vocab_size, embedding_dim)
        
        self.conv_0 = nn.Conv2d(in_channels = 1, 
                                out_channels = n_filters, 
                                kernel_size = (filter_sizes[0], embedding_dim))
        
        self.conv_1 = nn.Conv2d(in_channels = 1, 
                                out_channels = n_filters, 
                                kernel_size = (filter_sizes[1], embedding_dim))
        
        self.conv_2 = nn.Conv2d(in_channels = 1, 
                                out_channels = n_filters, 
                                kernel_size = (filter_sizes[2], embedding_dim))
        
        self.fc = nn.Linear(len(filter_sizes) * n_filters, output_dim)
        
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, text):
                
        #text = [batch size, sent len]
        
        embedded = text
                
        #embedded = [batch size, sent len, emb dim]
        
        embedded = embedded.unsqueeze(1)
        
        #embedded = [batch size, 1, sent len, emb dim]
        
        conved_0 = F.relu(self.conv_0(embedded).squeeze(3))
        conved_1 = F.relu(self.conv_1(embedded).squeeze(3))
        conved_2 = F.relu(self.conv_2(embedded).squeeze(3))
            
        #conved_n = [batch size, n_filters, sent len - filter_sizes[n] + 1]
        
        pooled_0 = F.max_pool1d(conved_0, conved_0.shape[2]).squeeze(2)
        pooled_1 = F.max_pool1d(conved_1, conved_1.shape[2]).squeeze(2)
        pooled_2 = F.max_pool1d(conved_2, conved_2.shape[2]).squeeze(2)
        
        #pooled_n = [batch size, n_filters]
        
        cat = self.dropout(torch.cat((pooled_0, pooled_1, pooled_2), dim = 1))

        #cat = [batch size, n_filters * len(filter_sizes)]
            
        return self.fc(cat)

def binary_accuracy(preds, y):
    """
    Returns accuracy per batch, i.e. if you get 8/10 right, this returns 0.8, NOT 8
    """

    #round predictions to the closest integer
    rounded_preds = torch.round(torch.sigmoid(preds))
    correct = (rounded_preds == y).float() #convert into float for division 
    acc = correct.sum() / len(correct)
    return acc

import copy

def clones(module, N):
    "Produce N identical layers."
    return nn.ModuleList([copy.deepcopy(module) for _ in range(N)])

import math
from torch.autograd import Variable

def attention(query, key, value, mask=None, dropout=None):
    "Compute 'Scaled Dot Product Attention'"
    d_k = query.size(-1)
    scores = torch.matmul(query, key.transpose(-2, -1)) \
             / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, -1e9)
    p_attn = F.softmax(scores, dim = -1)
    if dropout is not None:
        p_attn = dropout(p_attn)
    return torch.matmul(p_attn, value), p_attn


class MultiHeadedAttention(nn.Module):
    def __init__(self, h, d_model, dropout=0.1):
        "Take in model size and number of heads."
        super(MultiHeadedAttention, self).__init__()
        assert d_model % h == 0
        # We assume d_v always equals d_k
        self.d_k = d_model // h
        self.h = h
        self.linears = clones(nn.Linear(d_model, d_model), 4)
        self.attn = None
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, query, key, value, mask=None):
        "Implements Figure 2"
        if mask is not None:
            # Same mask applied to all h heads.
            mask = mask.unsqueeze(1)
        nbatches = query.size(0)

        # 1) Do all the linear projections in batch from d_model => h x d_k
        query, key, value = \
            [l(x).view(nbatches, -1, self.h, self.d_k).transpose(1, 2)
             for l, x in zip(self.linears, (query, key, value))]

        # 2) Apply attention on all the projected vectors in batch.
        x, self.attn = attention(query, key, value, mask=mask,
                                 dropout=self.dropout)

        # 3) "Concat" using a view and apply a final linear.
        x = x.transpose(1, 2).contiguous() \
            .view(nbatches, -1, self.h * self.d_k)
        x = torch.squeeze(x)
        return self.linears[-1](x)

class PositionwiseFeedForward(nn.Module):
    "Implements FFN equation."
    def __init__(self, d_model, d_ff, dropout=0.1):
        super(PositionwiseFeedForward, self).__init__()
        self.w_1 = nn.Linear(d_model, d_ff)
        self.w_2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        return self.w_2(self.dropout(F.relu(self.w_1(x))))

class Encoder(nn.Module):
    "Core encoder is a stack of N layers"

    def __init__(self, layer, N):
        super(Encoder, self).__init__()
        self.layers = clones(layer, N)
        self.norm = LayerNorm(layer.size)

    def forward(self, x, mask):
        "Pass the input (and mask) through each layer in turn."
        for layer in self.layers:
            x = layer(x, mask)
        return self.norm(x)

class LayerNorm(nn.Module):
    "Construct a layernorm module (See citation for details)."
    def __init__(self, features, eps=1e-6):
        super(LayerNorm, self).__init__()
        self.a_2 = nn.Parameter(torch.ones(features))
        self.b_2 = nn.Parameter(torch.zeros(features))
        self.eps = eps

    def forward(self, x):
        # mean = torch.Tensor(x.mean(-1, keepdims=True)).to('cuda')
        # std = torch.Tensor(x.std(-1, keepdims=True)).to('cuda')
        # x = torch.Tensor(x).to('cuda')
        mean = x.mean(-1,keepdim=True)
        std = x.std(-1,keepdim=True)
        return self.a_2 * (x - mean) / (std + self.eps) + self.b_2

class SublayerConnection(nn.Module):
    """
    A residual connection followed by a layer norm.
    Note for code simplicity we apply the norm first as opposed to last.
    """
    def __init__(self, size, dropout):
        super(SublayerConnection, self).__init__()
        self.norm = LayerNorm(size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, sublayer):
        "Apply residual connection to any sublayer function that maintains the same size."
        return x + self.dropout(sublayer(self.norm(x)))

class EncoderLayer(nn.Module):
    #Encoder is made up of two sublayers, self-attn and feed forward (defined below)
    def __init__(self, size, self_attn, feed_forward, dropout):
        super(EncoderLayer, self).__init__()
        self.self_attn = self_attn
        self.feed_forward = feed_forward
        self.sublayer = clones(SublayerConnection(size, dropout), 2)
        self.size = size

    def forward(self, x, mask):
        x = self.sublayer[0](x, lambda x: self.self_attn(x, x, x, mask))
        return self.sublayer[1](x, self.feed_forward)

class TransformerEncoder(nn.Module):
    

    def __init__(self, encoder, src_embed, d_model, n_class):
        super(TransformerEncoder, self).__init__()
        self.encoder = encoder
        self.src_embed = src_embed
        self.linear = nn.Linear(d_model, n_class)

    def forward(self, src, src_mask):
        "Take in and process masked src and target sequences."
        enc = self.encoder(src, src_mask)
        # flat = enc.reshape(-1).unsqueeze(0)
        lin = self.linear(enc)
        result = F.softmax(lin, dim=1)
        return result

SRC_VOCAB=1
N_CLASS=1
D_MODEL=embedding_size
D_FF=1024
N = 6
H=8
DROP_OUT=0.1

def make_model(src_vocab, N,
               d_model, d_ff, h, dropout, n_class):
    "Helper: Construct a model from hyperparameters."
    c = copy.deepcopy
    attn = MultiHeadedAttention(h, d_model)
    ff = PositionwiseFeedForward(d_model, d_ff, dropout)
    #position = PositionalEncoding(d_model, dropout)
    model = TransformerEncoder(
        Encoder(EncoderLayer(d_model, c(attn), c(ff), dropout), N),
        src_vocab,
        d_model,
        n_class
    )

    # This was important from their code.
    # Initialize parameters with Glorot / fan_avg.
    for p in model.parameters():
        if p.dim() > 1:
            nn.init.xavier_uniform(p)
    return model