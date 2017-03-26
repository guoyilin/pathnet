from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys

import tensorflow as tf

import input_data
import pathnet

import numpy as np

FLAGS = None


def train():
  # Import data
  mnist = input_data.read_data_sets(FLAGS.data_dir,
                                    one_hot=True,
                                    fake_data=FLAGS.fake_data)
  total_tr_data, total_tr_label = mnist.train.next_batch(mnist.train._num_examples);
  total_ts_data, total_ts_label = mnist.test.next_batch(mnist.test._num_examples);
  # Gathering 5,6 Data
  tr_data_5_6=total_tr_data[(total_tr_label[:,5]==1.0)|(total_tr_label[:,6]==1.0)];
  for i in range(len(tr_data_5_6)):
    for j in range(len(tr_data_5_6[0])):
      rand_num=np.random.rand()*2;
      if(rand_num<1):
        if(rand_num<0.5):
          tr_data_5_6[i,j]=0.0;
        else:
          tr_data_5_6[i,j]=1.0;
  tr_label_5_6=total_tr_label[(total_tr_label[:,5]==1.0)|(total_tr_label[:,6]==1.0)];
  tr_label_5_6=tr_label_5_6[:,5:7]; tr_5_6_flag=0;
  ts_data_5_6=total_ts_data[(total_ts_label[:,5]==1.0)|(total_ts_label[:,6]==1.0)];
  for i in range(len(ts_data_5_6)):
    for j in range(len(ts_data_5_6[0])):
      rand_num=np.random.rand()*2;
      if(rand_num<1):
        if(rand_num<0.5):
          ts_data_5_6[i,j]=0.0;
        else:
          ts_data_5_6[i,j]=1.0;
  ts_label_5_6=total_ts_label[(total_ts_label[:,5]==1.0)|(total_ts_label[:,6]==1.0)];
  ts_label_5_6=ts_label_5_6[:,5:7];
  
  ## TASK 1 (5,6 CLASSIFICATION)
  sess = tf.InteractiveSession()
  # Create a multilayer model.

  # Input placeholders
  with tf.name_scope('input'):
    x = tf.placeholder(tf.float32, [None, 784], name='x-input')
    y_ = tf.placeholder(tf.float32, [None, 2], name='y-input')

  with tf.name_scope('input_reshape'):
    image_shaped_input = tf.reshape(x, [-1, 28, 28, 1])
    tf.summary.image('input', image_shaped_input, 2)

  # geopath_examples
  geopath=pathnet.geopath_initializer(FLAGS.L,FLAGS.M);
  
  # fixed weights list
  fixed_list=np.ones((FLAGS.L,FLAGS.M),dtype=str);
  for i in range(FLAGS.L):
    for j in range(FLAGS.M):
      fixed_list[i,j]='0';    
  
  # reinitializing weights list
  rein_list=np.ones((FLAGS.L,FLAGS.M),dtype=str);
  for i in range(FLAGS.L):
    for j in range(FLAGS.M):
      rein_list[i,j]='0';    
  
  # Input Layer
  """
  input_weights=pathnet.module_weight_variable([784,FLAGS.filt]);
  input_biases=pathnet.module_bias_variable([FLAGS.filt]);
  net = pathnet.nn_layer(x,input_weights,input_biases,'input_layer');
  """

  # Hidden Layers
  weights_list=np.zeros((FLAGS.L,FLAGS.M),dtype=object);
  biases_list=np.zeros((FLAGS.L,FLAGS.M),dtype=object);
  for i in range(FLAGS.L):
    for j in range(FLAGS.M):
      if(i==0):
        weights_list[i,j]=pathnet.module_weight_variable([784,FLAGS.filt]);
        biases_list[i,j]=pathnet.module_bias_variable([FLAGS.filt]);
      else:
        weights_list[i,j]=pathnet.module_weight_variable([FLAGS.filt,FLAGS.filt]);
        biases_list[i,j]=pathnet.module_bias_variable([FLAGS.filt]);
  
  for i in range(FLAGS.L):
    layer_modules_list=np.zeros(FLAGS.M,dtype=object);
    for j in range(FLAGS.M):
      if(i==0):
        layer_modules_list[j]=pathnet.module(x, weights_list[i,j], biases_list[i,j], 'layer'+str(i+1)+"_"+str(j+1))*geopath[i,j];
      else:
        layer_modules_list[j]=pathnet.module(net, weights_list[i,j], biases_list[i,j], 'layer'+str(i+1)+"_"+str(j+1))*geopath[i,j];
    net=np.sum(layer_modules_list);
    
  """
  with tf.name_scope('dropout'):
    keep_prob = tf.placeholder(tf.float32)
    tf.summary.scalar('dropout_keep_probability', keep_prob)
    dropped = tf.nn.dropout(hidden1, keep_prob)
  """
  
  # Do not apply softmax activation yet, see below.
  output_weights=pathnet.module_weight_variable([FLAGS.filt,2]);
  output_biases=pathnet.module_bias_variable([2]);
  y = pathnet.nn_layer(net,output_weights,output_biases,'output_layer', act=tf.identity);

  with tf.name_scope('cross_entropy'):
    diff = tf.nn.softmax_cross_entropy_with_logits(labels=y_, logits=y)
    with tf.name_scope('total'):
      cross_entropy = tf.reduce_mean(diff)
  tf.summary.scalar('cross_entropy', cross_entropy)
  # Need to learn variables
  #var_list_to_learn=[]+input_weights+input_biases+output_weights+output_biases;
  var_list_to_learn=[]+output_weights+output_biases;
  for i in range(FLAGS.L):
    for j in range(FLAGS.M):
      if (fixed_list[i,j]=='0'):
        var_list_to_learn+=weights_list[i,j]+biases_list[i,j];
        
  with tf.name_scope('train'):
    train_step = tf.train.AdamOptimizer(FLAGS.learning_rate).minimize(
        cross_entropy,var_list=var_list_to_learn)
    #train_step = tf.train.GradientDescentOptimizer(FLAGS.learning_rate).minimize(
    #    cross_entropy,var_list=var_list_to_learn)
        

  with tf.name_scope('accuracy'):
    with tf.name_scope('correct_prediction'):
      correct_prediction = tf.equal(tf.argmax(y, 1), tf.argmax(y_, 1))
    with tf.name_scope('accuracy'):
      accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
  tf.summary.scalar('accuracy', accuracy)

  # Merge all the summaries and write them out to /tmp/tensorflow/mnist/logs/mnist_with_summaries (by default)
  merged = tf.summary.merge_all()
  train_writer = tf.summary.FileWriter(FLAGS.log_dir + '/train', sess.graph)
  test_writer = tf.summary.FileWriter(FLAGS.log_dir + '/test')
  tf.global_variables_initializer().run()
  def feed_dict(train,tr_5_6_flag=0):
    """Make a TensorFlow feed_dict: maps data onto Tensor placeholders."""
    if train or FLAGS.fake_data:
      xs=tr_data_5_6[tr_5_6_flag:tr_5_6_flag+16,:]; ys=tr_label_5_6[tr_5_6_flag:tr_5_6_flag+16,:];
      k = FLAGS.dropout
    else:
      xs=ts_data_5_6;ys=ts_label_5_6;
      k = 1.0
    return {x: xs, y_: ys}
    #return {x: xs, y_: ys, keep_prob: k}

  for i in range(FLAGS.max_steps):
    # First Candidate
    acc_geo1_tr=0;
    for j in range(FLAGS.T-1):
      summary_geo1_tr, _, acc_geo1_tmp = sess.run([merged, train_step,accuracy], feed_dict=feed_dict(True,tr_5_6_flag))
      tr_5_6_flag=(tr_5_6_flag+16)%len(tr_data_5_6);
      acc_geo1_tr+=acc_geo1_tmp;
    run_options_geo1 = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
    run_metadata_geo1 = tf.RunMetadata()
    summary_geo1_tr, _, acc_geo1_tmp = sess.run([merged, train_step,accuracy],
                              feed_dict=feed_dict(True,tr_5_6_flag),
                              options=run_options_geo1,
                              run_metadata=run_metadata_geo1)
    tr_5_6_flag=(tr_5_6_flag+16)%len(tr_data_5_6);
    acc_geo1_tr+=acc_geo1_tmp;
    summary_geo1_ts, acc_geo1 = sess.run([merged, accuracy], feed_dict=feed_dict(False))
    
    # Compatition between two cases
    if(True):
      train_writer.add_summary(summary_geo1_tr, i);
      train_writer.add_run_metadata(run_metadata_geo1, 'step%03d' % i);
      test_writer.add_summary(summary_geo1_ts, i);
      print('Accuracy at step %s: %s' % (i, acc_geo1));
      print('Training Accuracy at step %s: %s' % (i, acc_geo1_tr/FLAGS.T));
      if(acc_geo1_tr/FLAGS.T >= 0.998):
        print('Learning Done!!');
        print('Optimal Path is as followed.');
        break;
  iter_task1=i;      
  
  print("Entire Iter:"+str(iter_task1));

  train_writer.close()
  test_writer.close()


def main(_):
  if tf.gfile.Exists(FLAGS.log_dir):
    tf.gfile.DeleteRecursively(FLAGS.log_dir)
  tf.gfile.MakeDirs(FLAGS.log_dir)
  train()


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--fake_data', nargs='?', const=True, type=bool,
                      default=False,
                      help='If true, uses fake data for unit testing.')
  parser.add_argument('--learning_rate', type=float, default=0.001,
                      help='Initial learning rate')
  parser.add_argument('--max_steps', type=int, default=1000,
                      help='Number of steps to run trainer.')
  parser.add_argument('--dropout', type=float, default=0.9,
                      help='Keep probability for training dropout.')
  parser.add_argument('--data_dir', type=str, default='/tmp/tensorflow/mnist/input_data',
                      help='Directory for storing input data')
  parser.add_argument('--log_dir', type=str, default='/tmp/tensorflow/mnist/logs/pathnet',
                      help='Summaries log directory')
  parser.add_argument('--M', type=int, default=3,
                      help='The Number of Modules per Layer')
  parser.add_argument('--L', type=int, default=3,
                      help='The Number of Layers')
  parser.add_argument('--N', type=int, default=3,
                      help='The Number of Selected Modules per Layer')
  parser.add_argument('--T', type=int, default=50,
                      help='The Number of epoch per each geopath')
  parser.add_argument('--filt', type=int, default=20,
                      help='The Number of Filters per Module')
  parser.add_argument('--candi', type=int, default=64,
                      help='The Number of Candidates of geopath')
  FLAGS, unparsed = parser.parse_known_args()
  tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
