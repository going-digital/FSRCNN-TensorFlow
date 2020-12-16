import tensorflow.compat.v1 as tf
from utils import gradient_sensitive_loss, tf_ms_ssim

class Model(object):

  def __init__(self, config):
    self.name = "ESPCN"
    self.model_params = [64, 32] #[64, 32, 28]
    self.scale = config.scale
    self.radius = config.radius
    self.padding = config.padding
    self.images = config.images
    self.batch = config.batch
    self.label_size = config.label_size

  def model(self):
    d = self.model_params
    m = len(d) + 2

    # Feature Extraction
    size = self.padding + 1
    weights = tf.get_variable('w1', shape=[size, size, 1, d[0]], initializer=tf.variance_scaling_initializer(0.1))
    biases = tf.get_variable('b1', initializer=tf.zeros([d[0]]))
    conv = tf.nn.conv2d(self.images, weights, strides=[1,1,1,1], padding='VALID', data_format='NHWC')
    conv = tf.nn.bias_add(conv, biases, data_format='NHWC')
    conv = self.prelu(conv, 1)

    # Mapping (# mapping layers = m)
    for i in range(3, m):
      weights = tf.get_variable('w{}'.format(i), shape=[3, 3, d[i-3], d[i-2]], initializer=tf.variance_scaling_initializer(2))
      biases = tf.get_variable('b{}'.format(i), initializer=tf.zeros([d[i-2]]))
      conv = tf.nn.conv2d(conv, weights, strides=[1,1,1,1], padding='SAME', data_format='NHWC')
      conv = tf.nn.bias_add(conv, biases, data_format='NHWC')
      conv = self.prelu(conv, i)

    # Sub-pixel convolution
    size = self.radius * 2 + 1
    deconv_weights = tf.get_variable('deconv_w', shape=[size, size, d[-1], self.scale**2], initializer=tf.variance_scaling_initializer(0.01))
    deconv_biases = tf.get_variable('deconv_b', initializer=tf.zeros([self.scale**2]))
    deconv = tf.nn.conv2d(conv, deconv_weights, strides=[1,1,1,1], padding='SAME', data_format='NHWC')
    deconv = tf.nn.bias_add(deconv, deconv_biases, data_format='NHWC')
    deconv = tf.depth_to_space(deconv, self.scale, name='pixel_shuffle', data_format='NHWC')

    return deconv

  def prelu(self, _x, i):
    """
    PreLU tensorflow implementation
    """
    alphas = tf.get_variable('alpha{}'.format(i), _x.get_shape()[-1], initializer=tf.constant_initializer(0.2), dtype=tf.float32)

    return tf.nn.relu(_x) - alphas * tf.nn.relu(-_x)

  def loss(self, Y, X):
    return gradient_sensitive_loss(Y, X)
