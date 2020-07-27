##################################################################################################
#Draft Code
#Author：CE JU
##################################################################################################
import numpy as np
import random
import h5py
import os

from torch.autograd import Variable
import torch
import torch.nn.functional as F
import torch.nn as nn


import warnings
warnings.filterwarnings('ignore')
np.random.seed(0)


#%% Deep conv net - Baseline 1
class deepConvNet(nn.Module):
    '''
    Deep Convnet architecture:
        The expected input during runtime is in a formate:
            miniBatch x 1 x electroldes x time points
        During initialization set:
            nChan : number of electrodes
            nTime : number of samples
            nClasses: number of classes
    '''
    def convBlock(self, inF, outF, dropoutP, kernalSize,  *args, **kwargs):
        return nn.Sequential(
            nn.Dropout(p=dropoutP),
            nn.Conv2d(inF, outF, kernalSize, bias= False, *args, **kwargs),
            nn.BatchNorm2d(outF),
            nn.ELU(),
            nn.MaxPool2d((1,3), stride = 3)
            )

    def firstBlock(self, outF, dropoutP, kernalSize, nChan, *args, **kwargs):
        return nn.Sequential(
                nn.Conv2d(1,outF, kernalSize, padding = 0, *args, **kwargs),
                nn.Conv2d(10, 10, (nChan, 1), padding = 0, bias= False),
                nn.BatchNorm2d(outF),
                nn.ELU(),
                nn.MaxPool2d((1,3), stride = 3)
                )

    def lastBlock(self, inF, outF, kernalSize, *args, **kwargs):
        return nn.Sequential(
                nn.Conv2d(inF, outF, kernalSize, *args, **kwargs),
                nn.LogSoftmax(dim = 1))

    def calculateOutSize(self, model, nChan, nTime):
        '''
        Calculate the output based on input size.
        model is from nn.Module and inputSize is a array.
        '''
        data = torch.rand(1,1,nChan, nTime)
        model.eval()
        out = model(data).shape
        return out[2:]

    def __init__(self, nChan, nTime, nClass = 2, dropoutP = 0.25, *args, **kwargs):
        super(deepConvNet, self).__init__()

        kernalSize = (1,1)
        nFilt_FirstLayer = 10
        nFiltLaterLayer = [10, 10, 10, 10]

        firstLayer = self.firstBlock(nFilt_FirstLayer, dropoutP, kernalSize, nChan)
        middleLayers = nn.Sequential(*[self.convBlock(inF, outF, dropoutP, kernalSize)
            for inF, outF in zip(nFiltLaterLayer, nFiltLaterLayer[1:])])

        self.allButLastLayers = nn.Sequential(firstLayer, middleLayers)

        self.fSize = self.calculateOutSize(self.allButLastLayers, nChan, nTime)
        self.lastLayer = self.lastBlock(nFiltLaterLayer[-1], nClass, (1, self.fSize[1]))

    def forward(self, x):

        x = self.allButLastLayers(x)
        x = self.lastLayer(x)
        x = torch.squeeze(x, 3)
        x = torch.squeeze(x, 2)

        return x
		

def EEGNet_experients(cov_data, labels, index, fold, subject):
	#import model 

	#random_index = np.arange(cov_data.shape[0])
	#np.random.shuffle(random_index)

	cov_data_train = cov_data[index != fold].reshape((cov_data[index != fold].shape[0], 1, cov_data[index != fold].shape[1], cov_data[index != fold].shape[2]))
	cov_data_test  = cov_data[index == fold].reshape((cov_data[index == fold].shape[0], 1, cov_data[index == fold].shape[1], cov_data[index == fold].shape[2]))


	input_data_train = Variable(torch.from_numpy(cov_data_train)).float()
	input_data_test = Variable(torch.from_numpy(cov_data_test)).float()
	target_train = Variable(torch.LongTensor(labels[index != fold]))
	target_test  = Variable(torch.LongTensor(labels[index == fold]))

	model = deepConvNet(nChan=32, nTime=161)

	lr = 0.1
	old_loss = 1000
	iteration = 0
	#for iteration in range(100):
	while np.abs(old_loss) > 0.01:
		iteration += 1

		logits = model(input_data_train)
		output = F.log_softmax(logits, dim = -1)
		loss = F.nll_loss(output, target_train)
		pred = output.data.max(1, keepdim=True)[1]
		correct = pred.eq(target_train.data.view_as(pred)).long().cpu().sum()

		model.zero_grad()
		loss.backward()

		if iteration % 10 == 0:
			print('Iteration {} loss: {:4f}'.format(iteration, loss.item()))
			lr = max(0.99*lr, 0.005)

		with torch.no_grad():
			for param in model.parameters():
				param -= lr * param.grad

		if np.abs(loss.item()-old_loss) < 1e-6: break
		old_loss = loss.item()

	logits = model(input_data_test)
	output = F.log_softmax(logits, dim = -1)
	loss = F.nll_loss(output, target_test)
	pred = output.data.max(1, keepdim=True)[1]
	correct_test = pred.eq(target_test.data.view_as(pred)).long().cpu().sum()

	print('Subject {} (Fold {}) Classification Accuracy: {:4f}.'.format(subject, fold, correct_test.item()/pred.shape[0]))
	print('--------------------------------------')

	return correct_test.item()/pred.shape[0]



if __name__ == '__main__':

	data  = np.load('raw_data/normalized_original_epoch_data_train.npy')
	label = np.load('raw_data/train_label.npy')
	index = np.load('index.npy')


	accuracy = []
	all_accuracy = []

	for subject in range(89, 90):
		accuracy = []
		for fold in range(1, 6):
			cov_data_subject = data[subject]
			label_subject  	 = label[subject]
			accuracy.append(EEGNet_experients(cov_data_subject, label_subject, index[subject], fold, subject))
		all_accuracy.append(np.mean(np.array(accuracy)))

	print('All Accuracy: ', all_accuracy) 
	print('Average Classification Accuracy: {:4f}.'.format(np.array(all_accuracy).mean()))


