##################################################################################################
#FTL Draft Code for Subject-specific Analysis
#Author：CE JU
#Date  : April 20, 2020
#Paper : Ce Ju et al., Federated Transfer Learning for EEG Signal Classification, IEEE EMBS 2020.
#Description: Test on all 108 subjects with all baselines. 
##################################################################################################
import numpy as np
import random
import h5py
import os
import model
from torch.autograd import Variable
import torch
import datetime
import torch.nn.functional as F
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import scipy.io as sio

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

# mne import
from mne import Epochs, pick_types, events_from_annotations
from mne.io import concatenate_raws
from mne.io.edf import read_raw_edf
from mne.datasets import eegbci
from mne.event import find_events
from mne.decoding import CSP

# pyriemann import
from pyriemann.classification import MDM, TSclassifier,FgMDM
from pyriemann.estimation import Covariances

from sklearn.model_selection import cross_val_score, KFold
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn import svm

import warnings
warnings.filterwarnings('ignore')


def SPD_experients(cov_data,labels):
	import model

	random_index = np.arange(cov_data.shape[0])
	np.random.shuffle(random_index)

	cov_data = cov_data[random_index,:,:]
	labels = labels[random_index]

	split_num = int(np.floor(cov_data.shape[0]*0.8))
	cov_data_train = cov_data[0:split_num,:,:]
	cov_data_test  = cov_data[split_num:cov_data.shape[0],:,:]

	print('split_num: ', split_num)
	print('rest_num: ', labels.shape[0]-split_num)
	print('-------------------------------------------------------')

	input_data_train = Variable(torch.from_numpy(cov_data_train)).double()
	input_data_test = Variable(torch.from_numpy(cov_data_test)).double()
	target_train = Variable(torch.LongTensor(labels[0:split_num]))
	target_test = Variable(torch.LongTensor(labels[split_num:labels.shape[0]]))

	model = model.SPDNetwork()

	for _ in range(500):

		stime = datetime.datetime.now()
		logits = model(input_data_train)
		output = F.log_softmax(logits, dim = -1)
		loss = F.nll_loss(output, target_train)
		pred = output.data.max(1, keepdim=True)[1]
		correct = pred.eq(target_train.data.view_as(pred)).long().cpu().sum()
		loss.backward()
		lr = 0.1
		model.update_para(lr)
		etime = datetime.datetime.now()
		dtime = etime.second - stime.second

	logits = model(input_data_test)
	output = F.log_softmax(logits, dim = -1)
	loss = F.nll_loss(output, target_test)
	pred = output.data.max(1, keepdim=True)[1]
	correct_test = pred.eq(target_test.data.view_as(pred)).long().cpu().sum()
	return correct_test.item()/pred.shape[0]



if __name__ == '__main__':

	data=np.load('raw_data/normalized_original_train_sample.npy')
	epoch_data_train = np.load('raw_data/normalized_original_epoch_data_train.npy')
	label=np.load('raw_data/train_label.npy')
	index = np.load('index.npy')

	#good_subject_index =[0, 1, 6, 7, 14, 28, 30, 32, 33, 34, 41, 47, 51, 53, 54, 55, 59, 61, 69, 70, 71, 72, 79, 84, 85, 92, 103]
	#cov_data_good = np.concatenate(data[good_subject_index], axis=0)
	#labels_good = np.concatenate(label[good_subject_index], axis=0)
	#epochs_data_train_good = np.concatenate(epoch_data_train[good_subject_index], axis=0)

	FULL_MDM=[]
	FULL_FGMDM =[]
	FULL_TSC =[]
	FULL_CSP_lr =[]
	FULL_CSP_svm =[]

	#for bad_subject_index in [2, 8, 16, 17, 22, 23, 27, 35, 37, 38, 39, 40, 44, 46, 57, 62, 63, 66, 73, 75, 76, 77, 89, 95, 96, 98, 100, 101]:
	for bad_subject_index in range(108):
		#bad_subject_index = [2, 8, 16, 17, 22, 23, 27, 35, 37, 38, 39, 40, 44, 46, 57, 62, 63, 66, 73, 75, 76, 77, 89, 95, 96, 98, 100, 101]
		#bad_subject_index = 2
		#cov_data_bad = np.concatenate(data[bad_subject_index], axis=0)
		#labels_bad = np.concatenate(label[bad_subject_index], axis=0)
		#epochs_data_train_bad = np.concatenate(epoch_data_train[bad_subject_index], axis=0)
		cov_data_bad = data[bad_subject_index]
		labels_bad   = label[bad_subject_index]
		epochs_data_train_bad = epoch_data_train[bad_subject_index]


		MDM_record = []
		FGMDM_record = []
		TSC_record = []
		CSP_lr_record = []
		CSP_svm_record = []


		for fold in range(1,6):
			train = cov_data_bad[index[bad_subject_index]!=fold]
			train_CSP = epochs_data_train_bad[index[bad_subject_index]!=fold]
			train_label = labels_bad[index[bad_subject_index]!=fold]


			test = cov_data_bad[index[bad_subject_index]==fold]
			test_CSP = epochs_data_train_bad[index[bad_subject_index]==fold]
			test_label = labels_bad[index[bad_subject_index]==fold]

			box_length = np.sum([index[bad_subject_index]==fold])

			mdm = MDM(metric=dict(mean='riemann', distance='riemann'))

			mdm.fit(train, train_label)
			pred = mdm.predict(test)

			print('MDM: {:4f}'.format(np.sum(pred==test_label)/box_length))
			MDM_record.append(np.sum(pred==test_label)/box_length)
			print('-----------------------------------------')

			Fgmdm = FgMDM(metric=dict(mean='riemann', distance='riemann'))

			Fgmdm.fit(train, train_label)
			pred = Fgmdm.predict(test)

			print('FGMDM: {:4f}'.format(np.sum(pred==test_label)/box_length))
			FGMDM_record.append(np.sum(pred==test_label)/box_length)
			print('-----------------------------------------')


			clf = TSclassifier()
			clf.fit(train, train_label)
			pred = clf.predict(test)

			print('TSC: {:4f}'.format(np.sum(pred==test_label)/box_length))
			TSC_record.append(np.sum(pred==test_label)/box_length)
			print('-----------------------------------------')


			lr = LogisticRegression()
			csp = CSP(n_components=4, reg='ledoit_wolf', log=True)
			clf = Pipeline([('CSP', csp), ('LogisticRegression', lr)])
			clf.fit(train_CSP, train_label)
			pred = clf.predict(test_CSP)


			print('CSP_lr: {:4f}'.format(np.sum(pred==test_label)/box_length))
			CSP_lr_record.append(np.sum(pred==test_label)/box_length)
			print('-----------------------------------------')



			lr = svm.SVC(kernel='rbf')
			csp = CSP(n_components=4, reg='ledoit_wolf', log=True)
			clf = Pipeline([('CSP', csp), ('svc', lr)])
			clf.fit(train_CSP, train_label)
			pred = clf.predict(test_CSP)

			print('CSP_svm: {:4f}'.format(np.sum(pred==test_label)/box_length))
			CSP_svm_record.append(np.sum(pred==test_label)/box_length)
			print("------------------------------------------------------------------------")

		FULL_MDM.append(np.mean(MDM_record))
		FULL_TSC.append(np.mean(TSC_record))
		FULL_FGMDM.append(np.mean(FGMDM_record))
		FULL_CSP_lr.append(np.mean(CSP_lr_record))
		FULL_CSP_svm.append(np.mean(CSP_svm_record))

	print('MDM Record: ', FULL_MDM)
	print('R-Kernel Record: ', FULL_FGMDM)
	print('TSC Record: ', FULL_TSC)
	print('CSP_lr Record: ', FULL_CSP_lr)
	print('CSP_svm Record: ', FULL_CSP_svm)

	print('-----------------------')


	print('MDM: ', np.mean(FULL_MDM))
	print('R-Kernel: ', np.mean(FULL_FGMDM))
	print('TSC: ', np.mean(FULL_TSC))
	print('CSP_lr: ', np.mean(FULL_CSP_lr))
	print('CSP_svm: ', np.mean(FULL_CSP_svm))


		