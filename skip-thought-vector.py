from keras.layers          import Lambda, Input, Dense, GRU, LSTM, RepeatVector
from keras.layers.core     import Flatten
from keras.callbacks       import LambdaCallback 
from keras.optimizers      import SGD, RMSprop, Adam
from keras.layers.wrappers import Bidirectional as Bi
from keras.layers.wrappers import TimeDistributed as TD
from keras.layers          import merge, dot, multiply, concatenate, add, Activation
from keras.regularizers    import l2
from keras.layers.core     import Reshape
from keras.layers.normalization import BatchNormalization as BN
from keras.layers.core     import Dropout 
from keras.layers.embeddings import Embedding
from keras.models import Model
import keras.backend as K
import numpy as np
import random
import sys
import pickle
import json
import glob
import copy
import os
import re
import time
import concurrent.futures
import threading 

inputs      = Input( shape=(100,256) ) 
encoded     = Bi( GRU(300, activation='relu', return_sequences=False, dropout=0.1, recurrent_dropout=0.1) )( inputs )
encoded     = Dense(2012, activation='relu')( encoded )
encoded     = Dense(2012, activation='relu')( encoded )
encoded     = Dense(1012, activation='tanh')( encoded )
encoder     = Model(inputs, encoded)

decoded_1   = Bi( GRU(300, activation='relu', dropout=0.1, recurrent_dropout=0.1, return_sequences=True) )( RepeatVector(100)( encoded ) )
decoded_1   = TD( Dense(2024, activation='relu') )( decoded_1 )
decoded_1   = TD( Dense(2024, activation='relu') )( decoded_1 )
decoded_1   = TD( Dense(256, activation='linear') )( decoded_1 )

decoded_2   = Bi( GRU(300, activation='relu', dropout=0.1, recurrent_dropout=0.1, return_sequences=True) )( RepeatVector(100)( encoded ) )
decoded_2   = TD( Dense(2024, activation='relu') )( decoded_2 )
decoded_2   = TD( Dense(2024, activation='relu') )( decoded_2 )
decoded_2   = TD( Dense(256, activation='linear') )( decoded_2 )

skipthought = Model( inputs, [decoded_1, decoded_2] )
skipthought.compile( optimizer=Adam(), loss='mse' )
  
buff = None
now  = time.strftime("%H_%M_%S")
def callback(epoch, logs):
  global buff
  buff = copy.copy(logs)
  print(buff)
  # with open('../logs/loss_%s.log'%now, 'a+') as f:
  #   f.write('%s\n'%str(buff))
batch_callback = LambdaCallback(on_epoch_end=lambda batch,logs: callback(batch,logs) )

def train():
  triples = pickle.load( open('triples.pkl','rb') )
  Xs, ys1, ys2 = [], [], []
  for x, y1, y2 in triples[:32000]:
    Xs.append(x)
    ys1.append(y1)
    ys2.append(y2)
  Xs, ys1, ys2 = map(lambda x:np.array(x), [Xs, ys1, ys2])
  
  decay =  0.005
  baseline = 0.0001
  for count in range(200):
    lr = baseline*(1.0 - count*decay)
    skipthought.optimizer = Adam(lr=lr)
    skipthought.fit( Xs, [ys1, ys2], \
                          epochs=1,\
                          batch_size=300, \
                          validation_split=0.02, \
                          callbacks=[batch_callback] )
    loss = buff['loss']
    skipthought.save_weights('models/%0.09f_%0.12f_%09d.h5'%(loss,lr, count,))

def predict():
  to_load = sorted( glob.glob('../models/*.h5') ).pop() 
  skipthought.load_weights( to_load )
  t = threading.Thread(target=loader, args=())
  t.start()
  while True:
    if DATASET_POOL == []:
      print('no buffers so delay some seconds')
      time.sleep(1.)
      continue

    x, y1, y2, name = DATASET_POOL.pop(0)
    
    vecs = encoder.predict( x )
    for v in vecs.tolist():
      print( v )

  
  
if __name__ == '__main__':
  if '--train' in sys.argv:
    train()

  if '--predict' in sys.argv:
    predict()
