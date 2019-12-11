from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import sys
from classifier import training

datadir = './pre_img'
modeldir = './model/20170511-185253.pb'
classifier_filename = './class/classifier.pkl'
print ("Start Training")
obj=training(datadir,modeldir,classifier_filename)
get_file=obj.main_train()
sys.exit("All Done")
