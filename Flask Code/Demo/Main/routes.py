from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from flask import render_template, request, Blueprint
from demo.models import Post
from werkzeug import secure_filename
import tensorflow as tf
from scipy import misc
import cv2
import numpy as np
import facenet
import detect_face
import os
import time
import pickle
import sys
from PIL import Image, ImageEnhance 
from datetime import datetime
import numpy as np
from flask_login import login_required 

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
def home():
    # page = request.args.get('page', 1, type=int)
    # posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    # return render_template('home.html', posts=posts)
    return render_template('home.html')



@main.route("/result", methods=['POST'])
@login_required 
def result():
    path = './demo/static/'
    final_names=[];
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    output_csv_path = "/home/koli/Desktop/SPL-3-v1/flask codes/demo/static/output.csv"
    csv_file="file_name.csv"
    
    f = request.files['file']
    img_path=f.filename
    f.save(secure_filename(img_path))
    input_frame = cv2.imread(img_path)
    cv2.imwrite(os.path.join(path, str(timestamp)+img_path), input_frame)
    output = str(timestamp)+'.png'

    modeldir = './model/20170511-185253.pb'
    classifier_filename = './class/classifier.pkl'
    npy='./npy'
    train_img="./train_img"
    test_image_processsing = "/home/koli/Downloads/Facenet/test_imge_cropped/"
    #Create the identity filter, but with the 1 shifted to the right!
    kernel = np.zeros( (9,9), np.float32)
    kernel[4,4] = 2.0   #Identity, times two! 

    #Create a box filter:
    boxFilter = np.ones( (9,9), np.float32) / 81.0

    #Subtract the two:
    kernel = kernel - boxFilter
    with tf.Graph().as_default():
        gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
        sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
        with sess.as_default():
            pnet, rnet, onet = detect_face.create_mtcnn(sess, npy)

            minsize = 20  # minimum size of face
            threshold = [0.6, 0.7, 0.7]  # three steps's threshold
            factor = 0.709  # scale factor
            margin = 44
            frame_interval = 3
            batch_size = 1000
            image_size = 182
            input_image_size = 160
            d=0
            
            HumanNames = os.listdir(train_img)
            HumanNames.sort()


            print('Loading feature extraction model')
            facenet.load_model(modeldir)

            images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
            embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
            phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
            embedding_size = embeddings.get_shape()[1]


            classifier_filename_exp = os.path.expanduser(classifier_filename)
            with open(classifier_filename_exp, 'rb') as infile:
                (model, class_names) = pickle.load(infile)

            # video_capture = cv2.VideoCapture("akshay_mov.mp4")
            c = 0


            print('Start Recognition!')
            prevTime = 0
            # ret, frame = video_capture.read()
            frame = cv2.imread(img_path)
            frame = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)    #resize frame (optional)

            curTime = time.time()+1    # calc fps
            timeF = frame_interval

            if (c % timeF == 0):
                find_results = []

                if frame.ndim == 2:
                    frame = facenet.to_rgb(frame)
                frame = frame[:, :, 0:3]
                bounding_boxes, _ = detect_face.detect_face(frame, minsize, pnet, rnet, onet, threshold, factor)
                #print("bounding_boxes:", bounding_boxes)

                nrof_faces = bounding_boxes.shape[0]
                #print('Face Detected: %d' % nrof_faces)

                if nrof_faces > 0:
                    det = bounding_boxes[:, 0:4]
                    img_size = np.asarray(frame.shape)[0:2]

                    cropped = []
                    scaled = []
                    scaled_reshape = []
                    bb = np.zeros((nrof_faces,4), dtype=np.int32)

                    for i in range(nrof_faces):
                        emb_array = np.zeros((1, embedding_size))

                        bb[i][0] = det[i][0]
                        bb[i][1] = det[i][1]
                        bb[i][2] = det[i][2]
                        bb[i][3] = det[i][3]

                        # inner exception
                        if bb[i][0] <= 0 or bb[i][1] <= 0 or bb[i][2] >= len(frame[0]) or bb[i][3] >= len(frame):
                            print('face is too close')
                            continue

                        cropped.append(frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2], :])
                        cropped[i] = facenet.flip(cropped[i], False)
                        #image resize

                        #img = cropped[i]
                        #imResize = cv2.resize(img, (182,182))

                        #custom = cv2.filter2D(imResize, -1, kernel)
                        #cv2.imwrite(os.path.join(test_image_processsing , "file"+str(i)+".jpg"), custom)

                        #add for loop 
                        scaled.append(misc.imresize(cropped[i], (image_size, image_size), interp='bilinear'))
                        img1 = scaled[i]
                        cv2.imwrite(os.path.join(test_image_processsing , "file"+str(i)+".png"), img1)
                        scaled[i] = cv2.resize(scaled[i], (input_image_size,input_image_size),
                                               interpolation=cv2.INTER_CUBIC)
                        scaled[i] = facenet.prewhiten(scaled[i])
                        
                        scaled_reshape.append(scaled[i].reshape(-1,input_image_size,input_image_size,3))
                        #cv2.imwrite("./test_image_preprocesss"+"file"+str(i)+".jpg",cropped[i])
                        
                        #print("scaled_reshape::", scaled_reshape)
                        feed_dict = {images_placeholder: scaled_reshape[i], phase_train_placeholder: False}
                        emb_array[0, :] = sess.run(embeddings, feed_dict=feed_dict)
                        predictions = model.predict_proba(emb_array)
                        #print("predictions:", predictions)
                        best_class_indices = np.argmax(predictions, axis=1)
                        #print("best_class_indices:", best_class_indices)
                        best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
                        #print("Best Class Probabilities:", best_class_probabilities)
                        cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 255, 0), 2)    #boxing face
                       
                        
                        #plot result idx under box
                        text_x = bb[i][0]
                        text_y = bb[i][3] + 20
                        #print('Result Indices: ', best_class_indices[0])
                        #print(HumanNames)
                        for H_i in HumanNames:
                            #print("H_i:", H_i)
                            unknown_names =  "Unknown"
                            if HumanNames[best_class_indices[0]] == H_i and best_class_probabilities>0.16:
                                result_names = HumanNames[best_class_indices[0]]
                                final_names.append(result_names)
                                np.savetxt("./demo/static/file_name.csv", final_names, delimiter=",", fmt='%s', header="Name")
                                print(result_names)
                                cv2.putText(frame, result_names, (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                          0.3, (0, 0, 255), thickness=1, lineType=2)
                            """
                            else:
                                cv2.putText(frame, unknown_names, (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                            0.5, (0, 0, 255), thickness=1, lineType=2)
                            """
                            
                else:
                    print('Unable to align')
            #cv2.imshow('Image.jpg', frame)
            
            cv2.imwrite(os.path.join(path, output), frame)
            

        return render_template('result.html', input = str(timestamp)+img_path, output=output, final_names=final_names, csv_file=csv_file)
