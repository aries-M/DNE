import numpy as np
import tensorflow as tf
import math

class NodeEmbedding(object):
    def __init__(self, params, unigrams = None):
        self.embedding_size = params["embedding_size"]
        self.batch_size = params["batch_size"]
        self.num_nodes = params["num_nodes"]
        self.learn_rate = params["learn_rate"]
        self.optimizer = params["optimizer"] if "optimizer" in params else "GradientDescentOptimizer"
        self.tol = params["tol"] if "tol" in params else 0.001
        self.neighbor_size = params["neighbor_size"]
        self.negative_distortion = params["negative_distortion"]
        # self.num_sampled = max(1, int(params["num_sampled"] * self.num_nodes))
        self.num_sampled = params["num_sampled"]
        #print self.num_sampled
        #print self.num_nodes

        self.tensor_graph = tf.Graph()

        with self.tensor_graph.as_default():
            self.inputs = tf.placeholder(tf.int64, shape = [None])
            self.labels = tf.placeholder(tf.int64, shape = [None, self.neighbor_size])

            self.embeddings = tf.Variable(tf.random_uniform([self.num_nodes, self.embedding_size], -1.0, 1.0), name = "embeddings")
            self.nce_weights = tf.Variable(tf.truncated_normal([self.num_nodes, self.embedding_size], stddev = 1.0 / math.sqrt(self.embedding_size)))
            #self.nce_biases = tf.Variable(tf.zeros([self.num_nodes]))
            self.nce_biases = tf.zeros([self.num_nodes], tf.float32)
            embed = tf.nn.embedding_lookup(self.embeddings, self.inputs)

            if unigrams is None:
                self.loss = tf.reduce_mean(
                    tf.nn.nce_loss(weights = self.nce_weights, biases = self.nce_biases, labels = self.labels, inputs = embed, num_sampled = self.num_sampled, num_classes = self.num_nodes, num_true = self.neighbor_size))
            else:
                self.sampled_values = tf.nn.fixed_unigram_candidate_sampler(
                    true_classes = self.labels,
                    num_true = self.neighbor_size,
                    num_sampled = self.num_sampled,
                    unique = False,
                    range_max = self.num_nodes,
                    distortion = self.negative_distortion,
                    unigrams = unigrams
                        )
                self.loss = tf.reduce_mean(
                    tf.nn.nce_loss(
                        weights = self.nce_weights,
                        biases = self.nce_biases,
                        labels = self.labels,
                        inputs = embed, num_sampled = self.num_sampled,
                        num_classes = self.num_nodes,
                        num_true = self.neighbor_size, 
                        sampled_values = self.sampled_values
                        )
                    )

            self.train_step = getattr(tf.train, self.optimizer)(self.learn_rate).minimize(self.loss)

            #self.train_step = tf.train.AdamOptimizer(self.learnRate).minimize(self.cross_entropy)

    def train(self, get_batch, epoch_num = 10001, save_path = None):
        print("neural embedding: ")
        with tf.Session(graph = self.tensor_graph) as sess:
            sess.run(tf.global_variables_initializer())
            pre = float('inf')
            for i in xrange(epoch_num):
                batch_nodes, batch_y = get_batch(self.batch_size)
                self.train_step.run({self.inputs : batch_nodes, self.labels : batch_y})
                if (i % 100 == 0):
                    loss = self.loss.eval({self.inputs : batch_nodes, self.labels : batch_y})
                    if (i % 1000 == 0):
                        print(loss)
                    if abs(loss - pre) < self.tol:
                        break
                    else:
                        pre = loss
            if save_path is not None:
                saver = tf.train.Saver()
                saver.save(sess, save_path)
            return sess.run(self.embeddings), sess.run(self.nce_weights)

    def load_model(self, save_path):
        with tf.Session(graph = self.tensor_graph) as sess:
            saver = tf.train.Saver()
            saver.restore(sess, save_path)
            return sess.run(self.embeddings)

