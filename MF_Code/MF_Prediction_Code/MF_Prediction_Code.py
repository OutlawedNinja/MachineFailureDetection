## Import Library
import pickle
import numpy as np
import pandas as pd
from math import sqrt
import tensorflow as tf
from random import randint
import sklearn.linear_model
from matplotlib import pyplot
from keras.models import Sequential
from keras.models import load_model
from keras.layers import LSTM,Dense
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler

## Definitions

## Frame a sequence as a supervised learning problem
def timeseries_to_supervised(data, lag=1):
    df = pd.DataFrame(data)
    columns = [df.shift(i) for i in range(1, lag+1)]
    columns.append(df)
    df = pd.concat(columns, axis=1)
    df.fillna(0, inplace=True)
    return df

## Removing trend- Making Stationary
def difference(dataset, interval=1):
    diff = list()
    diff.append(0)
    for i in range(interval, len(dataset)):
        value = dataset[i] - dataset[i - interval]
        diff.append(value)
    return pd.Series(diff)

## Invert diffferenced value - Get Orignial Value
def inverse_difference(history, yhat, interval=1):
	return yhat + history[-interval]

## Scale Data
def scale(data):
    scaler = MinMaxScaler(feature_range=(-1, 1))
    scaler = scaler.fit(data.astype('float32'))
    data = data.reshape(data.shape[0],data.shape[1])
    scaled_X = scaler.transform(data)
    return scaler,scaled_X

## Inverse scailing for forecasted value
def inverse_scale(scaler,X,value):
    new_row = [x for x in X] + [value]
    array = np.array(new_row)
    array = array.reshape(1,len(array))
    inverted = scaler.inverse_transform(array)
    return inverted[0,-1]


## Predict output
def predict_data(data,scaler,model):
    global prev,trigger_count,trigger_value,zero_count
    ## Input Transformation
    data=data.reshape(data.shape[0],1)
    raw_values=data
    data=difference(data,1)
    data=timeseries_to_supervised(data,1)
    data=scaler.transform(data)
    for i in range(len(data)):
        X= data[i,1]
        X=X.reshape(1,1,1)
        ## Predicting the next possible value
        yhat = model.predict(X,1)
        ## Inverse Transformation
        yhat=inverse_scale(scaler,X,yhat)
        yhat=inverse_difference(raw_values,yhat,len(data)-i)
        print("Current Value is:",raw_values[i])
        print("Naxt value could be ",yhat)
        ## Calling Classifier to decide device on or off
        predict_alert(int(yhat))
        val=raw_values[i]
        ## Retraining Logic
        if val == 0:
            if 0 != prev:
                trigger_count+=1
                if trigger_value > prev:
                    trigger_value=prev
                if trigger_count >= trig:
                    retrain(raw_values)
                    trigger_count=0
            zero_count+=1
        prev=val

    return yhat

## Calling Classifier
def predict_alert(data):
    ## Load Model
    clf=pickle.load(open("clf","rb"))
    ## Predict Class
    y_pred=clf.predict([[data]])
    if np.array(y_pred[0]) == 0 :
        print("Alert-Chance of Over Memory Consumption")
    else:
        print("No Alert")
    return 0;

## Retraining the classifier for new threshold
def retrain(data):
    print("*"*33,"Retraining","*"*33)
    ## Data Preparation for Training
    data=pd.DataFrame(data,columns=["cpu_util"])
    temp_dataframe= pd.DataFrame(0, index=np.arange(len(data)), columns=["dev_status"])
    data=data.join(temp_dataframe)

    ## Augmenting training data for Off state Label
    for row in data.iterrows():
        if 0 == row[1][0] :
            row[1][0]=randint(trigger_value, int(trigger_value*1.4))
            row[1][1]=0
        elif row[1][0] >= trigger_value  :
            row[1][1]=0
        else:
            row[1][1]=1

    if zero_count < len(data)*0.5 :
        for i in range(int(len(data)*0.5) - zero_count):
            temp_dataframe=pd.DataFrame([[randint(trigger_value, int(trigger_value*1.4)), 0]], columns=["cpu_util","dev_status"])
            data = data.append(temp_dataframe, ignore_index=True)

    ## Data ready for retraining
    X=data.cpu_util
    Y=data.dev_status
    X= X.values.reshape(-1,1)
    Y = Y.values.reshape(-1,1)
    ## Model Trained for new data
    clf = sklearn.linear_model.LogisticRegressionCV()
    clf.fit(X,Y)
    ## Save the model
    pickle.dump(clf,open("clf","wb"))
    print("*"*33,"Retraining completed","*"*33)

## Loading Model( LSTM Model, Classifier Model )
lstm_model = load_model('my_model.h5')
scaler=pickle.load(open("scaler","rb"))

## Load input
data=pd.read_csv("Verify_Dataset.csv",header=None,names=["cpu_util"])


## Some Initialization
raw_values=data.cpu_util.values
prev=data.max()
trigger_value=int(data.max())
trigger_count=0
trig=5
zero_count=0

## Calling Prediction - Result :- Early alert or no alert
predict_data(raw_values,scaler,lstm_model)
