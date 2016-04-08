from theano import shared
import numpy as np
import theano
import theano.tensor as T
from layers import ConvLayer,PoolLayer,HiddenLayer,DropoutLayer, LogisticRegression
import theano.tensor.nnet as nn
from helper.utils import init_weight,init_bias,get_err_fn,count_params
from helper.optimizer import RMSprop

# theano.config.exception_verbosity="high"
dtype = T.config.floatX

class cnn(object):
    def __init__(self,rng,params,cost_function='mse',optimizer = RMSprop):

        lr=params["lr"]
        batch_size=params["batch_size"]
        sequence_length=params["seq_length"]

        # minibatch)
        X = T.matrix(name="input",dtype=dtype) # batch of sequence of vector
        Y = T.matrix(name="output",dtype=dtype) # batch of sequence of vector
        is_train = T.iscalar('is_train') # pseudo boolean for switching between training and prediction

        #CNN global parameters.
        subsample=(1,1)
        p_1=0.5
        border_mode="valid"
        cnn_batch_size=batch_size
        pool_size=(2,2)

        #Layer1: conv2+pool+drop
        filter_shape=(64,1,9,9)
        input_shape=(cnn_batch_size,1,120,60) #input_shape= (samples, channels, rows, cols)
        input= X.reshape(input_shape)
        c1=ConvLayer(rng, input,filter_shape, input_shape,border_mode,subsample, activation=nn.relu)
        p1=PoolLayer(c1.output,pool_size=pool_size,input_shape=c1.output_shape)
        dl1=DropoutLayer(rng,input=p1.output,prob=p_1)
        retain_prob = 1. - p_1
        test_output = p1.output*retain_prob
        d1_output = T.switch(T.neq(is_train, 0), dl1.output, test_output)

        #Layer2: conv2+pool
        filter_shape=(128,p1.output_shape[1],3,3)
        c2=ConvLayer(rng, d1_output, filter_shape,p1.output_shape,border_mode,subsample, activation=nn.relu)
        p2=PoolLayer(c2.output,pool_size=pool_size,input_shape=c2.output_shape)

        #Layer3: conv2+pool
        filter_shape=(128,p2.output_shape[1],3,3)
        c3=ConvLayer(rng, p2.output,filter_shape,p2.output_shape,border_mode,subsample, activation=nn.relu)
        p3=PoolLayer(c3.output,pool_size=pool_size,input_shape=c3.output_shape)

        #Layer4: hidden
        n_in= reduce(lambda x, y: x*y, p3.output_shape[1:])
        x_flat = p3.output.flatten(2)
        h1=HiddenLayer(rng,x_flat,n_in,1024,activation=nn.relu)

        #Layer4: hidden
        lreg=LogisticRegression(rng,h1.output,1024,42)
        self.output = lreg.y_pred

        self.params =c1.params+c2.params+c3.params+h1.params+lreg.params

        cost=get_err_fn(self,cost_function,Y)
        L2_reg=0.0001
        L2_sqr = theano.shared(0.)
        for param in self.params:
            L2_sqr += (T.sum(param[0] ** 2)+T.sum(param[1] ** 2))

        cost += L2_reg*L2_sqr

        _optimizer = optimizer(cost, self.params, lr=lr)
        self.train = theano.function(inputs=[X,Y,is_train],outputs=cost,updates=_optimizer.getUpdates(),allow_input_downcast=True)
        self.predictions = theano.function(inputs = [X,is_train], outputs = self.output,allow_input_downcast=True)
        self.n_param=count_params(self.params)