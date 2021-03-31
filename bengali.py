# -*- coding: utf-8 -*-
"""bengali.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rhz1WwFk89YPMpX1xfWWbFyyjzTpXOHB

# **Task 2 - Sentiment Classifier & Transfer Learning (10 points)**
## **Imports**
"""

# Imports
import torch
torch.manual_seed(10)
from torch.autograd import Variable
import pandas as pd
import numpy as np
import sklearn as sk
import re
import itertools
import warnings
warnings.filterwarnings("ignore")
from matplotlib import pyplot as plt
import nltk
import torch.nn as  nn
import torch.optim as optim
import torch.nn.functional as F

from google.colab import drive
drive.mount('/content/drive')
import sys
sys.path.append('/content/drive/MyDrive/Colab Notebooks')

import modelinput

"""## **2.2.1 Get the data (0.5 points)**
The downloaded file
"""

from google.colab import files
upload = files.upload()
data = pd.read_csv("bengali_hatespeech.csv",sep=',')
data1 = data.iloc[0:19000,:]

#Split off a part of the Bengali corpus such that it roughly equals the Hindi corpus in size and distribution of classes
from sklearn.model_selection import train_test_split
x, y = data1['sentence'], data1['hate']
X_TRAIN,x_test,Y_TRAIN,y_test=train_test_split(x,y,train_size=0.25,random_state=123)
X_TRAIN = X_TRAIN.values #roughtly the same number of sentences
Y_TRAIN = Y_TRAIN.values #roughtly the same number of labels
result = pd.value_counts(Y_TRAIN)
#print(Y_TRAIN)

# using a small development set
x_train_dev=X_TRAIN[1900:3000]
y_train = Y_TRAIN[1900:3000]
result = pd.value_counts(y_train)
print(result)
print(len(x_train_dev))

"""2.2.2clean the data"""

#clean the data
uploaded = files.upload()
stopwords = pd.read_csv('stopwords-bn.txt',header=None)
def clean_the_data(data):
  new_list=[]
  punc=r'''!()-[]{};:'"\,<>./?@#$%^&*_“~'''
  stop_words=stopwords[0].tolist()
  for i in range(0,len(data)):
    # Punctuations removal
    new=' '.join(word for word in data[i].split() if word[0] not in punc)
    new = ' '.join(re.sub("(\w+:\/\/\S+)", " ", new).split())
    new = ' '.join(re.sub(r"\b\d+\b", " ", new).split())
    new = ' '.join(re.sub("[\.\,\!\?\:\;\-\=\#\%\…\\u200d\।।]", " ", new).split())
    new = ' '.join(re.sub("[\U0001F600-\U0001F64F]"," ",new).split()) # emotions
    new = ' '.join(re.sub("[\U0001F300-\U0001F5FF]"," ",new).split()) # symbols & pictographs                           
    new = ' '.join(re.sub("[\U0001F680-\U0001F6FF]"," ",new).split()) # transport & map symbols                         
    new = ' '.join(re.sub("[\U0001F1E0-\U0001F1FF]"," ",new).split()) # flags (iOS)  
    new = ' '.join(re.sub("[\U00002702-\U000027B0]"," ",new).split())  
    new = ' '.join(re.sub("[\U000024C2-\U0001F251]"," ",new).split()) 
    new = ' '.join(re.sub("[\U00001F92C]"," ",new).split())                                                
    # Converting into lowercase
    new= new.lower()
    # Removing stop words
    new=' '.join(word for word in new.split() if word not in stop_words)
    # Appending to the text list
    new_list.append(new)
  return new_list

new_list = clean_the_data(x_train_dev)
#print(new_list)

nltk.download('punkt')

# Tokenizes each sentence by implementing the nltk tool
new_list_new = [nltk.tokenize.word_tokenize(x) for x in new_list]
#print(new_list_new[0])

"""2.2.3Build the vocabulary """

V=modelinput.vocabulary(new_list_new)
#print(V)

"""returns one-hot encoding"""

def word_to_one_hot(word):
  words = V.keys()
  str_to_int = dict((c, i) for i, c in enumerate(words))
  integer_encoded = [str_to_int[string] for string in [word]]
  # one hot encode
  onehot_encoded = []
  for value in integer_encoded:
	     letter = [0 for _ in range(len(V))]
	     letter[value] = 1
	     onehot_encoded.append(letter)
  #onehot_encoded.long()
  return onehot_encoded
  pass

"""2.2.4Subsampling"""

Words = {}
i=0
for s in range(len(new_list_new)):
  n=new_list_new[s]
  for y in range(len(n)):
    w=new_list_new[s][y]
    Words[w] = i
    i+=1
    y+=1
  s+=1
W2=list(Words)
def sampling_prob(word):
    frac = W2.count(word)/len(W2)
    prob = (np.sqrt(frac/0.000001) + 1) * (0.000001/frac)
    return prob
    pass

""" 2.2.5Skip-Grams"""

#from bndatapro import get_target_context
def get_target_context(sentence):
    word_lists=[]
    for i in range(len(sentence)):
       w=sentence[i]
       p_sample = sampling_prob(w)
       threshold = np.random.random()
       #print(threshold)
       if p_sample > threshold:
         # the word is kept
         for n in range(2):
                # look back
            if (i-n-1)>=0:
              word_lists.append([w] + [sentence[i-n-1]])
                
                # look forward
            if (i+n+1)<len(sentence):
              word_lists.append([w]+[sentence[i+n+1]])
       else:
         # the word is dropped
         i+=1
    return word_lists
    pass

"""2.2.6Hyperparameters """

# Set hyperparameters
window_size = 2
embedding_size = 64
vocabulary_size=len(V)
print(len(V))
# More hyperparameters
learning_rate = 0.05
epochs = 20

from modelss import Word2Vec

"""2.2.7 Word2Vec model"""

net = modelinput.Word2Vec(embed_size=embedding_size, vocab_size=vocabulary_size)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
net = net.to(device)

W1 = net.input.weight
W2 = net.output.weight

"""2.2.8loss function and optimizer"""

optimizer = torch.optim.SGD(net.parameters(), lr=learning_rate)
criterion = nn.CrossEntropyLoss()

"""2.2.9training model"""

# load initial weights
window_size = 2
embedding_size = 64
losses = [torch.tensor(1., device=device)]
#losses.append(1)
losses_mean=np.mean([tensor.cpu() for tensor in losses])
def train():
  
  print("Training started")

train()

for epo in range(epochs):
  #while losses_mean> 0.006:
     losses_mean=np.mean([tensor.cpu() for tensor in losses])
     #mean = torch.mean(torch.stack(losses))
     #mean = mean.to(device)
     print("Loss: ", losses_mean)
     net.train() 
    
     for i in range(len(new_list_new)):
        # Define train procedure
        # step1:Skip-Grams
        sentence = new_list_new[i]
        idx_pairs = get_target_context(sentence)
        for target, context in idx_pairs:
        # step2:target one-hot encoding
           X = word_to_one_hot(target)
           X = torch.tensor(X)
           x1 = X[0]
           x1 = x1.to(device)
           #print(x1)
        # step3:Word2Vec
           y =net.forward(x1)
        
           Y = word_to_one_hot(context)
           Y = Y[0]
           y_ture = torch.tensor(Y)
           y_ture = y_ture.to(device)
        # step4:loss
           loss = criterion(y,y_ture)
           #print(loss)
           losses.append(loss.data)
           losses.pop(0)
           optimizer.zero_grad()
           loss.backward()
           optimizer.step()
          
        # step5:Backprop to update model parameters 
   
           
print("Training finished")

Weight3=[]
for i in range(len(V)-1):
  weight3=[]
  w=W1[i]
  for y in range(embedding_size):
    wei=w[y].item()
    weight3.append(wei)
  Weight3.append(weight3)
    

V2 = dict(zip(V, Weight3))

sentence_padding =[]
pad_idx = 0
padding_standard = max(new_list_new, key=len,default='')

#padding the sentence to the same length
for i in range(len(new_list_new)):
  temp_sentence = list()
  temp = new_list_new[i]
  while len(temp) < len(padding_standard):
      temp.insert(len(temp), pad_idx)
  sentence_padding.append(temp) 

#make sentences to the same size matrix using word embedding expression
sentence_train=[]
for i in range(len(sentence_padding)):
  temp_sentence = list()
  temp = new_list_new[i]
  for word in temp:
    if word in V2.keys():
      temp_sentence.append(V2[word])
    else:
      temp_sentence.append(np.zeros(embedding_size))
  sentence_train.append(temp_sentence)

print(np.shape(sentence_train))

sentence_train3=torch.tensor(sentence_train)

"""We create an instance of our CNN class."""

from modelinput import CNN
EMBEDDING_DIM = embedding_size 
N_FILTERS = 100
FILTER_SIZES = [2,3,4]
OUTPUT_DIM = 1
DROPOUT = 0.5

model = CNN(EMBEDDING_DIM, N_FILTERS, FILTER_SIZES, OUTPUT_DIM, DROPOUT)

"""Train the Model : The method of training is same as the previous one. We can initialize the values of optimizer and criterion (loss function)."""

optimizer1 = optim.Adam(model.parameters())

criterion1 = nn.BCEWithLogitsLoss()

model = model.to(device)
criterion1 = criterion1.to(device)

"""Apply the old classifer to the new data and print accuracy: We import a package called 'binary_accuracy' to calculate the accuracy. It returns accuracy per batch. For instance if 7/10 are correct repsonses, the output will be 0.7. Further, we define a function "evaluate(model)" for training our model."""

from modelinput import binary_accuracy
sentence_train3=sentence_train3.to(device,dtype=torch.float)
Y_train = torch.tensor(y_train).to(device)
def evaluate(model):
    
    epoch_loss = 0
    epoch_acc = 0
    
    model.eval()
    
    predictions = model(sentence_train3).squeeze(1)
            
    loss = criterion1(predictions, Y_train.float())
            
    acc = binary_accuracy(predictions, Y_train)

    epoch_loss += loss.item()
    epoch_acc += acc.item()
        
    return epoch_loss, epoch_acc 

model.load_state_dict(torch.load('/content/CNNweight.pt'))
test_loss, test_acc = evaluate(model)
print(f'Test Loss: {test_loss:.3f} | Test Acc: {test_acc*100:.2f}%')

"""retrain the model and print new accuracy"""

N_EPOCHS = 20
sentence_train3=sentence_train3.to(device,dtype=torch.float)
#train_iterator = iter(sentence_train1)
#best_valid_loss = float('inf')
Y_train = torch.tensor(y_train).to(device)
for epoch in range(N_EPOCHS):
    epoch_loss = 0
    epoch_acc = 0
    
    model.train()
  
    optimizer1.zero_grad()

    predictions = model.forward(sentence_train3).squeeze(1)    
    loss1 = criterion1(predictions, Y_train.float())
        
    acc = binary_accuracy(predictions, Y_train)

    loss1.backward()    
    optimizer1.step()
        
    epoch_loss += loss1.item()
    epoch_acc += acc.item()
    
    
    
    
    
    
    print(f'\tTrain Loss: {loss1:.3f} | Train Acc: {acc*100:.2f}%')

"""Transformer model for Bengali"""

import torch.nn as nn
import copy

def clones(module, N):
    "Produce N identical layers."
    return nn.ModuleList([copy.deepcopy(module) for _ in range(N)])

import math,copy
#doing the position encoding first
def positionalencoding1d(d_model, length):
   
    if d_model % 2 != 0:
        raise ValueError("Cannot use sin/cos positional encoding with "
                         "odd dim (got dim={:d})".format(d_model))
    pe = torch.zeros(length, d_model)
    position = torch.arange(0, length).unsqueeze(1)
    div_term = torch.exp((torch.arange(0, d_model, 2, dtype=torch.float) *
                         -(math.log(10000.0) / d_model)))
    pe[:, 0::2] = torch.sin(position.float() * div_term)
    pe[:, 1::2] = torch.cos(position.float() * div_term)

    return pe


posit = positionalencoding1d(64,219) # the shape of one padding sentence
posit = torch.tensor(posit,device=device)

AttInput=torch.empty(np.shape(sentence_train3))

for i in range(len(sentence_train3)):
   tar =sentence_train3[i]
   AttInput[i]= tar+posit
Input = AttInput[0:100,]

torch.cuda.empty_cache()
SRC_VOCAB=1
N_CLASS=1
D_MODEL=embedding_size
D_FF=1024
N = 6
H=8
DROP_OUT=0.1
model2 = modelinput.make_model(SRC_VOCAB,N,D_MODEL,D_FF,H,DROP_OUT, N_CLASS)
model2 = model2.to(device)
lr=0.005
criterion2 = nn.CrossEntropyLoss()
optimizer2 = torch.optim.Adam(model2.parameters(),lr)
N_EPOCHS = 10
for epoch in range(N_EPOCHS):
    epoch_loss2 = 0
    epoch_acc2 = 0   
  
    optimizer2.zero_grad()

    x = Input.to(device)
    y = torch.tensor(y_train[0:100], dtype=torch.long, device=device)
    y = y.unsqueeze(1)
    
    output = model2(x, None)
    loss2 = criterion2(output,y)
     

    loss2.backward()    
    optimizer2.step()
        
    epoch_loss2 += loss2.item()
   
    print(f'\tTrain Loss: {loss2:.3f}')